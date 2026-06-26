"""
The script is not clearly structured, but it fits the computation of HCC in the cluster.
"""

import argparse
import calendar
import datetime
import os
from pathlib import Path
import sys
import time
import tempfile

from dask.diagnostics import ProgressBar
import pandas as pd
import numpy as np
from upath import UPath
import xarray as xr
import zarr

if False:
    # Switch to true if running in the cluster
    # The `generalized_overlap` function is part of a script,
    # which can be used as a module, so I import it here.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #target_path = os.path.join(script_dir, '..', 'ccic_cc', 'scripts')
    #sys.path.insert(0, target_path)
    sys.path.insert(0, script_dir)
    # Not needed if the script is in the same directory as this one, but I keep it for clarity.

from CCIC_ERA5_collocation_nearestneighbour_average_all import generalized_overlap

GRID_LON = np.arange(-180, 181)
GRID_LAT = np.arange(-60, 61)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=Path, required=True)
    parser.add_argument('--output_zarr', type=Path, required=True)
    parser.add_argument('--threshold', type=float, default=0.360)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--month', type=int)
    parser.add_argument('--zipzarr', action='store_true')
    parser.add_argument('--host')
    args = parser.parse_args()

    assert not args.output_zarr.exists()

    expected_files = []
    for m in ([args.month] if args.month else [m for m in range(1, 13)]):
        expected_files += [
            args.input_dir / f'ccic_cpcir_{e.strftime("%Y%m%d%H%M")}.zarr'
            for e in pd.date_range(
                f'{args.year}-{m:02d}',
                pd.Timestamp(f'{args.year}-{m:02d}') + pd.Timedelta(days=calendar.monthrange(args.year, m)[1]),
                freq='1h',
                inclusive='left'
            )
        ]

    # assert all(e.exists() for e in expected_files), "Some expected files are missing."

    #with ProgressBar():
    hcc = None
    elapsed_time = 0
    for i, f in enumerate(expected_files):
        t_start = time.time()
        print(f'{datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}. Processing {i+1}/{len(expected_files)}, last iteration: {elapsed_time:03.1f} s', flush=True)#, end='\r')
        # cloud_prob_3d = xr.open_mfdataset(expected_files, engine='zarr', parallel=True).cloud_prob_3d
        if not args.zipzarr:
            with xr.open_zarr(f) as ds:
                cloud_prob_3d = ds.cloud_prob_3d.compute()
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                if args.host:
                    f_name = Path(f).name
                    bs = (Path(tmpdir) / f'{f_name}.zip').write_bytes(UPath(f'sftp://{args.host}/{f}.zip').read_bytes())
                    assert bs > 0, f"Failed to download {f}.zip from {args.host}"
                    f_path = Path(tmpdir) / f'{f_name}.zip'
                else:
                    f_path = f'{f}.zip'

                with zarr.ZipStore(f_path, mode='r') as store:
                    with xr.open_zarr(store) as ds:
                        cloud_prob_3d = ds.cloud_prob_3d.compute()

        data_3d = xr.where(
            np.isfinite(cloud_prob_3d),
            (cloud_prob_3d >= args.threshold).astype(cloud_prob_3d.dtype),
            np.nan
        )
        # Compute stratified cloud cover
        data_3d = (
            data_3d.groupby_bins('latitude', GRID_LAT)
            .mean(dim='latitude')
            .groupby_bins('longitude', GRID_LON)
            .mean(dim='longitude')
        )
        data_3d = data_3d.where(data_3d.altitude >= 6_000, 0)

        data_3d = data_3d.rename({'latitude_bins': 'latitude', 'longitude_bins': 'longitude'})
        data_3d['longitude'] = ('longitude', [e.mid for e in data_3d['longitude'].values])
        data_3d['latitude'] = ('latitude', [e.mid for e in data_3d['latitude'].values])

        # Calling .compute() here avoids excessive repetition in `generalized_overlap`,
        # I don't find a more elegant way to do this.
        # data_3d = data_3d.compute()

        hcc = xr.concat(
            (
                hcc,
                generalized_overlap(data_3d)
            ),
            'time'
        ) if (hcc is not None) else generalized_overlap(data_3d)
        elapsed_time = time.time() - t_start
    
    with ProgressBar():
        hcc['ymh'] = (
            'time',
            [
                f"{y}-{m:02d}-{h:04d}"
                for (y, m, h) in zip(hcc.time.dt.year.data, hcc.time.dt.month.data, hcc.time.dt.hour.data * 60 + hcc.time.dt.minute.data)
            ]
        )
        hcc_mean = hcc.groupby('ymh').mean('time').reset_coords(drop=True).to_dataset(name='hcc')
        hcc_count = hcc.groupby('ymh').count('time').reset_coords(drop=True).to_dataset(name='hcc_count')
        hcc = xr.merge((hcc_mean, hcc_count))
        hcc['ymh'] = (
            'ymh',
            [
                datetime.datetime.strptime(e[:-5], '%Y-%m') + datetime.timedelta(minutes=int(e.split('-')[-1]))
                for e in hcc['ymh'].data
            ]
        )
        hcc = hcc.rename({'ymh': 'time'})

        hcc = hcc.expand_dims({'threshold': [args.threshold]})

        try:
            hcc.to_zarr(args.output_zarr, zarr_format=2)
        except:
            hcc.to_netcdf(args.output_zarr.with_suffix('.nc'))
