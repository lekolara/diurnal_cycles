#!/usr/bin/env python3

import xarray as xr
import numpy as np
from pathlib import Path

def load_and_process_single_file(dataset_name, input ,varname_out="tiwp"):
    """Open one file, detect variable name, rename, compute hour-of-day coordinate."""
    ds = xr.open_dataset(input, decode_timedelta=True) #True for IMERG and ERA

    ds = ds.rename({"longitude": "lon", "latitude": "lat"})
        # Adjust longitudes to 0-360 if they are now from -180 to 180
    if ds.lon.min() < 0:
        ds = ds.assign_coords(lon=((ds.lon + 360) % 360)).sortby('lon')

    if dataset_name == "CCIC_TIWP" :
        # Detect variable name
        if "tiwp_stratified" in ds:
            var = "tiwp_stratified"
        else:
            raise ValueError(f"Cannot find tiwp variable in {input}")
        # Rename to unified name
        ds = ds.where(ds[var]>=0)
        ds = ds.rename({var: varname_out})
        # Rename longitude to lon and latitude to lat
        time_array = ds.tiwp.hour_of_day.values
        hours = (time_array / np.timedelta64(1, 'h')).astype(int) 
        # Replace the coordinate
        da = ds.assign_coords(hour_of_day=hours)
        # Collapse the 30-min bins into 24 hourly bins
        da_hourly = da.groupby('hour_of_day').mean()
        da_hourly=da_hourly.sortby("hour_of_day").tiwp
    elif dataset_name == "ERA5":
        if "total_column_cloud_ice_water" in ds and "total_column_snow_water" in ds:
            sum_var = ds["total_column_cloud_ice_water"] + ds["total_column_snow_water"]
            ds = sum_var.to_dataset(name=varname_out)
            ds = ds.where(ds[varname_out]>=0)
            da_hourly = ds.rename({"hour": "hour_of_day"}).tiwp
        else:
            raise ValueError(f"Cannot find tiwp variable in {input}")
    elif dataset_name == "DYAMOND":
        if "TIWP" in ds:
            var = "TIWP"
        ds = ds.where(ds[var]>=0)
        ds = ds.rename({var: varname_out})
        da_hourly = ds.rename({'hour': 'hour_of_day'}).tiwp

    return da_hourly

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

def build_diurnal_feb2020(dataset_name, input_root, output_file):
    input_root = Path(input_root)
    print(f"\n=== Building February 2020 diurnal for {dataset_name} ===")
    infile = input_root
    if not infile.exists():
        print(f"  WARNING: No file {infile}")
        return
    print(f"  Using {infile.name}")

    ds = xr.open_dataset(input, decode_timedelta=False) 
    ds = ds.rename({"longitude": "lon", "latitude": "lat"})
        # Adjust longitudes to 0-360 if they are now from -180 to 180
    if ds.lon.min() < 0:
        ds = ds.assign_coords(lon=((ds.lon + 360) % 360)).sortby('lon')

    
    diurnal = load_and_process_single_file(dataset_name, infile, varname_out="tiwp")
    lon_dim = 'longitude' if 'longitude' in diurnal.dims else 'lon'
    hour_dim = 'hour_of_day'
    pr_local = shift_diurnal_to_local_time(diurnal, hour_dim=hour_dim, lon_dim=lon_dim)
    final = pr_local.to_dataset(name='tiwp')
   
    print(f"\n=== Saving final diurnal → {output_file} ===")
    final.to_netcdf(output_file)
    print("Done.")

def build_dyamond_feb2020(model_name, input_root, output_file):
    
    input_root = Path(input_root)
    output_file = Path(output_file)

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Building February 2020 diurnal for DYAMOND model {model_name} ===")

    diurnal = load_and_process_single_file("DYAMOND", input_root, varname_out="tiwp") 

    lon_dim = 'longitude' if 'longitude' in diurnal.dims else 'lon'
    hour_dim = 'hour_of_day'
    pr_local = shift_diurnal_to_local_time(diurnal, hour_dim=hour_dim, lon_dim=lon_dim)
    final = pr_local.to_dataset(name='tiwp')
    if "leadtime" in final:
        final = final.drop_vars("leadtime")
    print(f"\n=== Saving final diurnal → {output_file} ===")
    final.to_netcdf(output_file)
    print("Done.")

if __name__ == "__main__":

    '''
    
     # Example for ERA5
    build_diurnal_feb2020(
        dataset_name="ERA5",
        input_root="/data/s5/users/lara/master_thesis/data/ERA5/2020/2020_02_era5_mean_1deg.nc",
        output_file="/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_feb2020.nc",
    )

    # Example for CCIC CPCIR TIWP
    build_diurnal_feb2020(
        dataset_name="CCIC_TIWP",
        input_root="/data/s5/users/lara/master_thesis/data/ccic/2020/ccic_cpcir_2020_02_monthlymean_1deg_tiwp.nc",
        output_file="/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_feb2020.nc",
    )

    '''
    # # DYAMOND models
    
    dyamond_models = ["ARPEGE", "GEOS", "GSAM", "ICON", "IFS", "MPAS", "GEM", "GFDL", "GRIST"]
    
    for model in dyamond_models:
        build_dyamond_feb2020(
            model_name=model,
            input_root=f"/data/s5/users/lara/master_thesis/data/DYAMOND/{model}/{model}_202002_1deg_tiwp.nc",
            output_file=f"/data/s5/users/lara/master_thesis/data/DYAMOND/{model}_diurnal_feb2020.nc",
        )

    
    
