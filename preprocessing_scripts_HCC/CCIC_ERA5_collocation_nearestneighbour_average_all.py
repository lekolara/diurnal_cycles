"""
Collocate CCIC data onto ERA5 grid for comparing low, mid, and high level clouds using
an approach where all the nearest neighbours in the ERA5 grid are averaged after the
probability of each one is thresholded. One can think of this method as an analogous to taking
the mean with the bucket resampling method of pyresample, but with an irregular grid.

A generalized vertical overlap assumption, also called exponential-random overlap, is used.

A note on args.era5_p_levels_file (args.era5_s_levels_file):
The source file is
'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'
('gs://gcp-public-data-arco-era5/co/single-level-reanalysis.zarr-v2'),
which is also the default. However, a local file containing the subset of
this Zarr with matching timestamps with CCIC data and only the necessary
variables can be advantageous. It has been observed that the connection
to the Google Cloud Storage bucket can stall. The connection to the bucket
might stall because of too many connections, reloads of Zarr
or because we are not working in a Google Cloud environment.
Perhaps a smart use of Dask and Xarray can prevent this situation,
but we found that downloading to disk was effective.

Update on 2025-03-03: Option to download ERA5 Zarr temporarily to disk.

Furthermore, we avoid import pansat (through importing ccic), because of
https://github.com/SEE-GEO/pansat/issues/117 which makes fsspec/gcsfs fail,
and we copy and paste the relevant code sections.
"""
import argparse
import concurrent.futures
import datetime
import multiprocessing
import logging
import pickle
import sys
import tempfile
import warnings

from dask.diagnostics import ProgressBar
import pandas as pd
from pyproj import Geod
import pyresample
import numpy as np
import tqdm
from upath import UPath as Path
import xarray as xr
import zarr

# Constant variables
# ENCODINGS is equivalent to importing the encoding from ccic
# but we avoid importing ccic because of
# https://github.com/SEE-GEO/pansat/issues/117
# (ccic imports pansat)
ENCODINGS = {
    k: {
        "compressor": zarr.Blosc(cname="lz4", clevel=9, shuffle=2),
        "scale_factor": 1 / 250,
        "_FillValue": 255,
        "dtype": "uint8"
    }
    for k in ['tcc', 'lcc', 'mcc', 'hcc']
}
GRAVITY = 9.80665 # m s-2

# Thresholds determined with the evaluation
THRESHOLD_CLOUD_PROB_2D = 0.484
THRESHOLD_CLOUD_PROB_3D = 0.348

# Chunks for ERA5_p_levels Zarr
CHUNKS_ERA5_P_LEVELS = {
    'time': 1,
    'latitude': 721,
    'longitude': 1440,
    'level': 37
}

# Functions
def compute_elevation(r_earth: xr.DataArray, h_level: xr.DataArray,
                      h_s: xr.DataArray) -> xr.DataArray:
    """
    Compute the altitude above the Earth's surface of a given geopotential height.

    Args:
        r_earth: the Earth's radius at the latitude of the grid
        h_level: the geopotential height of the level
        h_s: the geopotential height at the surface

    Returns the altitude above the Earth's surface of the given geopotential height.
    """
    alt_h_s = r_earth * h_s / (r_earth - h_s)
    
    alt_h_level = r_earth * h_level / (r_earth - h_level)

    return alt_h_level - alt_h_s


def compute_h_level(z: xr.DataArray, idx_level: xr.DataArray,
    gravity: float=GRAVITY) -> xr.DataArray:
    """
    Compute the geopotential height at the given pressure level.

    Args:
        z: geopotential
        idx_level: the pressure level index
        gravity: the gravity value
    
    Returns the geopotential height at the given pressure level.
    """
    return xr.DataArray(
        np.take_along_axis(
            z.transpose(..., 'level').data,
            idx_level.expand_dims('level').transpose(..., 'level').data,
            axis=-1
            )[..., 0] / gravity,
        coords={k: idx_level[k] for k in idx_level.dims}
    )


def geod2geoc(latitude_geodetic: np.ndarray[float], model: Geod=Geod(ellps='WGS84')) \
    -> tuple[np.ndarray[float], np.ndarray[float]]:
    """
    Convert geodetic coordinates to geocentric coordinates.
    
    Based on MATLAB `geod2geoc`.
    
    Args:
        latitude_geodetic: the geodetic latitudes
        model: the ellipsoid model to use

    Returns a tuple of (geocentric latitudes, radii with respect to centre)
    """
    a = model.a
    b = model.b
    e2 = model.es
    phi_geodetic = np.deg2rad(latitude_geodetic)
    phi_geocentric = np.arctan((1 - e2) * np.tan(phi_geodetic))
    latitude_geocentric = np.rad2deg(phi_geocentric)
    r = a * b / (np.sqrt((a * np.sin(phi_geocentric)) ** 2 + (b * np.cos(phi_geocentric)) ** 2))
    return latitude_geocentric, r


def map_elev_to_CCIC_bin_height(elev_level,
    CCIC_height_bin_edges=np.arange(21, dtype=np.float32) * 1e3) -> xr.DataArray:
    """
    Map an elevation above the Earth's surface to the CCIC height bins.
    """
    a = xr.DataArray(
        np.digitize(elev_level.data, CCIC_height_bin_edges),
        coords={k: elev_level[k] for k in elev_level.dims}
    ).astype(np.int8) - 1
    return a.transpose('time', 'values')

def map_to_irregularERA5(a: xr.DataArray, rows_idx: np.ndarray,
                cols_idx: np.ndarray, values_coords: np.ndarray=None) -> xr.DataArray:
    """
    Map a DataArray from a regular grid to the irregular ERA5 grid.

    Args:
        a: the DataArray to map
        rows_idx: row indexes defining the mapping from
            AreaDefinition to SwathDefinition
        cols_idx: column indexes defining the mapping from
            AreaDefinition to SwathDefinition
    
    Returns a new DataArray without `latitude` and `longitude`
        and instead `values` as the new dimension.
    """
    a = a.transpose(..., 'latitude', 'longitude')
    values_coords = np.arange(len(rows_idx)) if values_coords is None else values_coords
    return xr.DataArray(
        a.data[
            ...,
            rows_idx,
            cols_idx
        ],
        coords={
            k: a[k] for k in a.dims if k not in ['latitude', 'longitude']
        } | {'values': values_coords}
    )

def generalized_overlap(d: xr.DataArray, L_0: float=2e3) -> xr.DataArray:
    z = d.altitude.broadcast_like(d)
    c_i = d.isel(altitude=0)
    z_i = z.isel(altitude=0)
    gap_i = xr.zeros_like(c_i, dtype=bool)
    for i in range(1, d.altitude.size - 1):
        c_ip1 = d.isel(altitude=i)
        z_ip1 = z.isel(altitude=i)
        alpha = np.exp(- abs(z_ip1 - z_i) / L_0)
        c_r = c_i + c_ip1 - c_i * c_ip1
        c_g = alpha * np.maximum(c_i, c_ip1) + (1 - alpha) * c_r

        c_i = xr.where(
            gap_i,
            c_r,
            c_g
        )

        z_i = xr.where(
            c_ip1 > 0,
            z_ip1,
            z_i
        )
        gap_i = xr.where(
            np.isclose(c_ip1, 0) & ~np.isclose(c_i, 0),
            1,
            0
        )
    # Address any original NaN values
    c_i = xr.where(np.isfinite(d).all(dim='altitude'), c_i, np.nan)
    return c_i

def overlap_assumptions_wrapper(d: xr.DataArray, overlap_assumptions: str) -> xr.DataArray:
    if overlap_assumptions == 'gen':
        return generalized_overlap(d)
    elif overlap_assumptions == 'max':
        return d.max(dim='altitude')
    elif overlap_assumptions == 'ran':
        return 1 - (1 - d).prod(dim='altitude')
    elif overlap_assumptions == 'min':
        # clouds overlap minimum, so it's min(d.sum(dim='altitude'), 1), but we also want to preserve the NaN values for the cases where all values are NaN
        return xr.where(np.isfinite(d).all(dim='altitude'), d.sum(dim='altitude').clip(0, 1), np.nan)
    else:
        raise ValueError(f'Invalid overlap assumption: {overlap_assumptions}')

# Function wrapping the collocation process
def collocation(
    files: list[str], pbar_pos: int,
    era5_p_levels_gcpath: str,
    idx_era5regular2irregular_rows: np.ndarray,
    idx_era5regular2irregular_cols: np.ndarray,
    idx_ccic2era5_rows: np.ndarray,
    idx_ccic2era5_cols: np.ndarray,
    values_ccic2era5: np.ndarray,
    r_earth: xr.DataArray,
    zarr_output_directory: str,
    encodings: dict,
    threshold_cloud_prob_2d: float,
    threshold_cloud_prob_3d: float,
    overlap_assumptions: str='gen'
) -> None:

    # kwargs based on example from https://github.com/google-research/arco-era5
    kwargs = dict(
        chunks=None,
        storage_options=dict(token='anon')
    ) if era5_p_levels_gcpath.startswith('gs://') else dict()
    # Open variables defined above
    era5_p_levels = xr.open_zarr(
        era5_p_levels_gcpath,
        decode_timedelta=True,
        **kwargs
    )[
        [
            'geopotential_at_surface',
            'geopotential',
            'surface_pressure',
        ]
    ].chunk(CHUNKS_ERA5_P_LEVELS)

    hostname_output = zarr_output_directory.split("/")[2] if 'ssh://' in zarr_output_directory else None
    for f in tqdm.tqdm(files, position=pbar_pos, leave=True, ncols=80):
        # Open and load the CCIC file
        ds_gridsat = xr.open_zarr(f).load()

        # Subset and load the era5_p_levels to only the timestamp of the CCIC file
        ds_era5_p_levels = era5_p_levels.sel(time=ds_gridsat.time).load()

        # Broadcast ERA5 data to add missing dimensions
        levels, surface_pressure = xr.broadcast(
            ds_era5_p_levels.level,
            ds_era5_p_levels.surface_pressure
        )

        # Spatial mapping of ERA5 data from regular to irregular grid
        levels = map_to_irregularERA5(
            levels,
            idx_era5regular2irregular_rows,
            idx_era5regular2irregular_cols
        )

        surface_pressure = map_to_irregularERA5(
            surface_pressure,
            idx_era5regular2irregular_rows,
            idx_era5regular2irregular_cols
        )

        h_s = map_to_irregularERA5(
            ds_era5_p_levels.geopotential_at_surface / GRAVITY,
            idx_era5regular2irregular_rows,
            idx_era5regular2irregular_cols
        )

        z = map_to_irregularERA5(
            ds_era5_p_levels.geopotential,
            idx_era5regular2irregular_rows,
            idx_era5regular2irregular_cols
        )

        # and spatial mapping of the CCIC data to the irregular ERA5 grid
        ds_gridsat_resampled = xr.merge(
            (
                map_to_irregularERA5(
                    ds_gridsat.cloud_prob_2d,
                    idx_ccic2era5_rows,
                    idx_ccic2era5_cols,
                    values_ccic2era5
                ).to_dataset(name='cloud_prob_2d'),
                map_to_irregularERA5(
                    ds_gridsat.cloud_prob_3d,
                    idx_ccic2era5_rows,
                    idx_ccic2era5_cols,
                    values_ccic2era5
                ).to_dataset(name='cloud_prob_3d')
            ),
            compat='no_conflicts' # Avoid FutureWarning
        )

        data_2d = ds_gridsat_resampled.cloud_prob_2d
        data_3d = ds_gridsat_resampled.cloud_prob_3d
        # If thresholds specified, apply them to convert to binary mask (preserving invalid values)
        data_levels = {}
        if threshold_cloud_prob_2d >= 0:
            data_2d = xr.where(np.isfinite(data_2d), (data_2d >= threshold_cloud_prob_2d).astype(data_2d.dtype), np.nan)
        if threshold_cloud_prob_3d >= 0:
            data_3d = xr.where(np.isfinite(data_3d), (data_3d >= threshold_cloud_prob_3d).astype(data_3d.dtype), np.nan)

        # Compute stratified cloud cover
        data_2d = data_2d.groupby('values').mean()
        data_3d = data_3d.groupby('values').mean()

        # ERA5 defines low level cloud, mid level cloud and high level cloud as:
        # - low: pressure > 0.8 times the surface pressure
        # - high: pressure < 0.45 times the surface pressure
        # - middle: otherwise
        # Parameters 186, 187, and 188 in the ERA5 Parameter Database
        # We try to respect this as much as possible and find the corresponding
        # index for the pressure levels of low, mid, and high levels.
        # Note: `level` is in hPa, `surface_pressure` in Pa
        t_lcc = 0.8
        d_lcc = 100 * levels - t_lcc * surface_pressure
        idx_lcc = d_lcc.where(d_lcc > 0).argmin('level')
        t_hcc = 0.45
        d_hcc = 100 * levels - t_hcc * surface_pressure
        idx_hcc = d_hcc.where(d_hcc < 0).argmax('level')

        # Map the index of the pressure levels discriminating between
        # low and high levels, which by extension includes middle levels
        # to the index of the CCIC bin heights, taking into account
        # the surface of the Earth's as CCIC elevation is not with respect
        # to mean sea level but rather the Earth's surface
        h_lcc = compute_h_level(z, idx_lcc)
        elev_lcc = compute_elevation(r_earth, h_lcc, h_s)
        idx_lcc_ccic = map_elev_to_CCIC_bin_height(elev_lcc).sel(values=data_3d['values'].values)

        h_hcc = compute_h_level(z, idx_hcc)
        elev_hcc = compute_elevation(r_earth, h_hcc, h_s)
        idx_hcc_ccic = map_elev_to_CCIC_bin_height(elev_hcc).sel(values=data_3d['values'].values)

        # Compute and apply masks to compute statistics
        # for low, mid, and high level clouds
        altitude_idxs = xr.DataArray(
            np.arange(20),
            dims='altitude'
        ).broadcast_like(data_3d)

        mask_lcc = (altitude_idxs <= idx_lcc_ccic)
        mask_mcc = ((idx_lcc_ccic < altitude_idxs) & (altitude_idxs < idx_hcc_ccic))
        mask_hcc = (idx_hcc_ccic <= altitude_idxs)

        # Prepare data for each atmosphere group
        data_levels = {}
        for l, _mask in [('lcc', mask_lcc), ('mcc', mask_mcc), ('hcc', mask_hcc)]:
            data_levels[l] = data_3d.where(_mask, 0)
        data_levels['tcc_3D'] = data_3d

        # Apply overlapping assumptions
        cloud_cover_levels = {k: overlap_assumptions_wrapper(v, overlap_assumptions) for k, v in data_levels.items()}

        # Compile data
        ds_gridsat_xcc = xr.merge(
            [
                v.rename(k).astype('float32')
                for k, v in cloud_cover_levels.items()
            ] + [data_2d.rename('tcc').astype('float32')],
            compat='no_conflicts' # Avoid FutureWarning
        ).reset_coords(drop=True)

        output_path = str(Path(zarr_output_directory) / f'{Path(f).stem}_ERA5_nearestneighbour_avg_{overlap_assumptions}')
        output_path = Path(f'{output_path}_thres.zarr') if threshold_cloud_prob_2d > 0 else Path(f'{output_path}_prob.zarr')

        # This will fail if path is remote path
        if output_path.protocol == '':
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)

        if hostname_output:
            output_path = str(output_path).replace('ssh://', f'ssh://{hostname_output}')
        
        ds_gridsat_xcc.to_zarr(
            output_path,
            encoding=encodings
        )

def collocation_wrapper(args):
    return collocation(*args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Collocate CCIC data onto ERA5 grid.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--era5_mask', default='data/masks/mask_ERA5_GridSatArea.nc',
                        help='Obtained from `ERA5_mask.py`')
    parser.add_argument(
        '--workers', type=int, default=1,
        help='Number of workers to use'
    )
    parser.add_argument(
        '--era5_s_levels_file',
        help='ERA5 single levels file',
        default='gs://gcp-public-data-arco-era5/co/single-level-reanalysis.zarr-v2'
    )
    parser.add_argument(
        '--era5_p_levels_file',
        help='ERA5 pressure levels file',
        default='gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'
    )
    parser.add_argument(
        '--output_directory',
        default='/scratch/amell/ccic/analyses/data/CCIC_ERA5_collocation'
    )
    parser.add_argument(
        '--record_directory',
        default='/scratch/amell/ccic/record_cc/gridsat'
    )
    parser.add_argument(
        '--dtstart',
        required=True,
        type=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d')
    )
    parser.add_argument(
        '--dtend',
        required=True,
        type=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d')
    )
    parser.add_argument(
        '--ccic2era5_bucketmapping',
        default='data/mappings/ccic_to_irregular_era5_bucket_mapping.pickle',
        help='pickle file generated by `CCIC_ERA5_bucket_mapping.py`'
    )
    parser.add_argument(
        '--local_era5',
        help='If given, save the era5_p_levels Zarr temporarily to this directory'
    )
    parser.add_argument(
        '--manual_tmp_download',
        action='store_true',
        help="If given, manually limit the number of dask workers to download ERA5"
    )
    parser.add_argument(
        '--threshold_cloud_prob_2d',
        type=float,
        default=THRESHOLD_CLOUD_PROB_2D,
        help='Threshold for 2D cloud probability, if negative a Bernoulli trial is executed'
    )
    parser.add_argument(
        '--threshold_cloud_prob_3d',
        type=float,
        default=THRESHOLD_CLOUD_PROB_3D,
        help='Threshold for 3D cloud probability, if negative a Bernoulli trial is executed'
    )
    parser.add_argument(
        '--overlap_assumptions',
        type=str,
        default='gen',
        choices=['gen', 'max', 'ran', 'min'],
        help='Overlap assumptions to apply to the different levels of clouds'
    )

    args = parser.parse_args()

    hostname = args.record_directory.split('/')[2] if 'ssh://' in args.record_directory else ''

    assert (
        (0 < args.threshold_cloud_prob_2d < 1) and
        (0 < args.threshold_cloud_prob_3d < 1)
    ) or (
        (args.threshold_cloud_prob_2d == 0) and
        (args.threshold_cloud_prob_3d == 0)
    ), (
        'Thresholds must be in the range [0, 1] or 0 to use the raw probabilities as cloud fraction.'
    )

    # AreaDefinitions and SwathDefinitions
    # to make the spatial mapping simple and efficient

    # WARNING: ERA5 is given in longitudes in [0, 360),
    #          but if not given to pyresample in [-180, 180)
    #          the algorithm breaks
    era5_regular_areadef = pyresample.geometry.create_area_def(
        "era5_regular_grid",
        {"proj": "longlat", "datum": "WGS84"},
        area_extent=[-180 - 0.25 / 2, -90 - 0.25/2, 180 - 0.25 / 2, 90 + 0.25 / 2],
        resolution=0.25,
        units="degrees",
        description="ERA5 grid."
    )

    # We need the coordinates from the irregular ERA5 dataset, so we open it
    kwargs = dict(
        chunks=None,
        storage_options=dict(token='anon')
    ) if args.era5_s_levels_file.startswith('gs://') else dict()
    era5_s_levels = xr.open_zarr(
        args.era5_s_levels_file,
        decode_timedelta=True,
        **kwargs
    )

    # and the associated CCIC-ERA5 mask to restrict coordinates to CCIC grid
    mask = xr.open_dataset(args.era5_mask, engine='h5netcdf')

    # Address the [0, 360) -> [-180, 180) mapping and filtering coordinates
    # outside the CCIC grid
    era5_s_levels_longitudes = era5_s_levels.longitude.values
    era5_s_levels_longitudes = np.where(
        era5_s_levels_longitudes > 180,
        era5_s_levels_longitudes - 360,
        era5_s_levels_longitudes
    )[mask.mask.values]
    era5_s_levels_latitudes = era5_s_levels.latitude.values[mask.mask.values]

    # finally create the SwathDefintion for the irregular ERA5 grid
    era5_irregular_swath = pyresample.geometry.SwathDefinition(
        lons=era5_s_levels_longitudes,
        lats=era5_s_levels_latitudes
    )

    # Mapping indexs between AreaDefinitions and SwathDefinition
    # between regular and irregular ERA5 grids...
    idx_era5regular2irregular_rows, idx_era5regular2irregular_cols \
        = pyresample.utils.generate_nearest_neighbour_linesample_arrays(
        era5_regular_areadef,
        era5_irregular_swath,
        1e5 # Simply to not make the algorithm break
    )

    # ...and between CCIC and irregular ERA5 grids
    with open(args.ccic2era5_bucketmapping, 'rb') as handle:
        idx_ccic2era5_rows, idx_ccic2era5_cols, values_ccic2era5 = pickle.load(handle)


    # Open ERA5 pressure levels dataset and the three
    # variables needed from this dataset
    # kwargs based on example from https://github.com/google-research/arco-era5
    era5_p_levels_file = args.era5_p_levels_file
    kwargs = dict(
        chunks=None,
        storage_options=dict(token='anon')
    ) if era5_p_levels_file.startswith('gs://') else dict()
    era5_p_levels = xr.open_zarr(
        era5_p_levels_file,
        decode_timedelta=True,
        **kwargs
    )[
        [
            'geopotential_at_surface',
            'geopotential',
            'surface_pressure',
        ]
    ].chunk(CHUNKS_ERA5_P_LEVELS)

    # If applicable, download ERA5 Zarr to disk
    with tempfile.TemporaryDirectory(dir=args.local_era5) as tmpdir:
        # Everything in context manager, to ensure a proper cleanup if
        # the download or processing fails
        if args.local_era5:
            # Subset to the time range of interest
            era5_p_levels = era5_p_levels.sel(
                time=pd.date_range(args.dtstart, args.dtend, freq='3h').to_numpy()
            )
            era5_p_levels_file = Path(tmpdir) / 'era5_p_levels.zarr'
            logging.warning(f'Downloading ERA5 Zarr ({era5_p_levels.nbytes / 1024**3:.2f} GiB uncompressed) to {era5_p_levels_file}')
            if args.manual_tmp_download:
                # Process in chunks, otherwise it is memory hungry
                # and, moreover, it is not easy to get a progressbar
                for i_t in tqdm.tqdm(range((era5_p_levels.time.size // args.workers) + 1), ncols=80):
                    t = era5_p_levels.time.values[(i_t * args.workers):((i_t + 1) * args.workers)]
                    era5_p_levels.sel(time=t).to_zarr(
                        era5_p_levels_file,
                        append_dim='time' if Path(era5_p_levels_file).exists() else None
                    )
            else:
                with ProgressBar():
                    era5_p_levels.to_zarr(era5_p_levels_file)

        # Compute the radius of the Earth at the latitude of the ERA5 grid
        # handling geodetic coordinates
        _, r_earth = geod2geoc(era5_p_levels.latitude)

        # Map the radii values between ERA5 grids
        r_earth = xr.DataArray(
            r_earth.data[idx_era5regular2irregular_rows],
            coords={
                'values': np.arange(len(idx_era5regular2irregular_rows))
            }
        )

        gridsat_files = sorted([str(f).replace('ssh://',f'ssh://{hostname}') for f in Path(args.record_directory).glob('*/*.zarr') if (args.dtstart <= datetime.datetime.strptime(f.name, 'ccic_gridsat_%Y%m%d%H00.zarr') <= args.dtend)])

        print(f"{len(gridsat_files)} files from {args.record_directory} between {args.dtstart} and {args.dtend}")
        expected_output_files = [
            Path(args.output_directory) / f'{Path(f).stem}_ERA5_nearestneighbour_avg_{args.overlap_assumptions}_{"thres" if args.threshold_cloud_prob_2d > 0 else "prob"}.zarr'
            for f in gridsat_files
        ]
        gridsat_files = [f_in for f_in, f_out in zip(gridsat_files, expected_output_files) if not f_out.exists()]
        print(f"{len(expected_output_files) - len(gridsat_files)} files already exist in {args.output_directory}, skipping them")
        if len(gridsat_files) == 0:
            print("No files to process, exiting")
            sys.exit()
    
        print(f"Processing {len(gridsat_files)} files")

        # We are not able to use multiprocessing with the current approach, it stalls
        # multiprocessing.set_start_method('forkserver', force=True)
        # Process first file
        inputs = [
            (
                files,
                pbar_pos,
                str(era5_p_levels_file),
                idx_era5regular2irregular_rows,
                idx_era5regular2irregular_cols,
                idx_ccic2era5_rows,
                idx_ccic2era5_cols,
                values_ccic2era5,
                r_earth,
                args.output_directory,
                ENCODINGS,
                args.threshold_cloud_prob_2d,
                args.threshold_cloud_prob_3d,
                args.overlap_assumptions
            ) for pbar_pos, files in enumerate(np.array_split(gridsat_files, args.workers))
        ]

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=args.workers,
            mp_context=multiprocessing.get_context('spawn')
        ) as executor:
            futures = [executor.submit(collocation_wrapper, inp) for inp in inputs]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    # Do nothing, but only log error
                    logging.error(f'Error processing {future}: {e}')