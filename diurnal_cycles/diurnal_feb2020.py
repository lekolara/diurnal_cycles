#!/usr/bin/env python3

import xarray as xr
import numpy as np
from pathlib import Path

def load_and_process_single_file(filename, varname_out="pr", multiply=False):
    ds = xr.open_dataset(filename)
    if "precipitation" in ds:
        var = "precipitation"
    elif "total_precipitation" in ds:
        var = "total_precipitation"
    elif "pr" in ds:
        var = "pr"
    else:
        raise ValueError(f"Cannot find precipitation variable in {filename}")
    ds = ds.rename({var: varname_out})
    ds = ds.where(ds[varname_out]>=0)
    if multiply:
        ds[varname_out] = ds[varname_out] * 1000
    if not np.issubdtype(ds.time.dtype, np.datetime64):
        ds["time"] = xr.decode_cf(ds).time
    hours = ds["time"].dt.hour 
    ds = ds.assign_coords(hour_of_day=("time", hours.data))
    return ds

def shift_diurnal_to_local_time(da, hour_dim="hour_of_day", lon_dim="longitude"):
    nsteps = da[hour_dim].size
    deg_per_step = 360 / nsteps
    lons = da[lon_dim].values
    shifted = da.copy(deep=True)
    for i, lon in enumerate(lons):
        shift = int(np.round(lon / deg_per_step))
        shifted.loc[{lon_dim: lon}] = da.roll({hour_dim: shift}, roll_coords=False).loc[{lon_dim: lon}]
    return shifted

def compute_diurnal_mean(ds, var="pr"):
    # for era5 and imerg it just returns the same array but withou the time dimension
    diurnal = ds[var].groupby("hour_of_day").mean("time")
    return diurnal.sortby("hour_of_day")

def build_diurnal_feb2020(dataset_name, input_root, output_file, infile_name, multiply=False):
    input_root = Path(input_root)
    print(f"\n=== Building February 2020 diurnal for {dataset_name} ===")
    infile = input_root / infile_name
    if not infile.exists():
        print(f"  WARNING: No file {infile_name}")
        return
    print(f"  Using {infile.name}")
    ds = load_and_process_single_file(infile, varname_out="pr", multiply=multiply)
    diurnal = compute_diurnal_mean(ds)
    lon_dim = 'longitude' if 'longitude' in diurnal.dims else 'lon'
    hour_dim = 'hour_of_day'
    pr_local = shift_diurnal_to_local_time(diurnal, hour_dim=hour_dim, lon_dim=lon_dim)
    final = pr_local.to_dataset(name='pr')
    if "time_bnds" in final:
        final = final.drop_vars("time_bnds")
    print(f"\n=== Saving final diurnal → {output_file} ===")
    final.to_netcdf(output_file)
    print("Done.")

def build_dyamond_feb2020(model_name, input_root, output_file):
    
    input_root = Path(input_root)
    output_file = Path(output_file)
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Building February 2020 diurnal for DYAMOND model {model_name} ===")

    files = sorted(input_root.glob("202002*.nc"))
    if not files:
        print(f"  WARNING: No files for {model_name} in February 2020")
        return
    ds_list = [load_and_process_single_file(f, varname_out="pr", multiply=False) for f in files]
    ds = xr.concat(ds_list, dim="time")
    diurnal = compute_diurnal_mean(ds)
    lon_dim = 'longitude' if 'longitude' in diurnal.dims else 'lon'
    hour_dim = 'hour_of_day'
    pr_local = shift_diurnal_to_local_time(diurnal, hour_dim=hour_dim, lon_dim=lon_dim)
    final = pr_local.to_dataset(name='pr')
    if "time_bnds" in final:
        final = final.drop_vars("time_bnds")
    print(f"\n=== Saving final diurnal → {output_file} ===")
    final.to_netcdf(output_file)
    print("Done.")

if __name__ == "__main__":
    
    '''
    # ERA5
    build_diurnal_feb2020(
        dataset_name="ERA5",
        input_root="/scratch/leko/ERA5/ERA5_1_deg_diurnal/2020",
        output_file="/scratch/leko/ERA5/ERA5_1_deg_diurnal/ERA5_diurnal_feb2020.nc",
        infile_name="2020_02_ERA5_diurnal_mean.nc",
        multiply=True,
    )
    # IMERG
    build_diurnal_feb2020(
        dataset_name="IMERG",
        input_root="/scratch/leko/IMERG/IMERG_1_deg_diurnal/2020",
        output_file="/scratch/leko/IMERG/IMERG_1_deg_diurnal/IMERG_diurnal_feb2020.nc",
        infile_name="2020_02_IMERG_diurnal_mean.nc",
        multiply=False,
    )
    '''
    # DYAMOND models
    #
    #dyamond_models = ["ARPEGE", "GEOS", "gSAM", "ICON", "IFS", "SHiELD"]
    dyamond_models = ["gSAM"]

    for model in dyamond_models:
        build_dyamond_feb2020(
            model_name=model,
            input_root=f"/scratch/nilsmu/DYAMOND_precipitation/data/latlon_grid_1deg/{model}",
            output_file=f"/scratch/leko/DYAMOND/diurnal/{model}_diurnal_feb2020.nc",
        )

    
    
