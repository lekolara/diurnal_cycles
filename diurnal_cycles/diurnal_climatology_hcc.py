#!/usr/bin/env python3

import xarray as xr
import numpy as np
from pathlib import Path
import os


def load_and_process_single_file(ds, varname_out="hcc"):
    """Open one file, detect variable name, rename, compute hour-of-day coordinate."""
    if 'hcc' in ds:
        var = "hcc"
    elif 'high_cloud_cover' in ds:
        var = "high_cloud_cover"

    # Rename to unified name
    ds = ds.where(ds[var]>=0)
    ds = ds.rename({var: varname_out})

    # Rename longitude to lon and latitude to lat if necessary
    if "longitude" in ds.coords and "latitude" in ds.coords:
        ds = ds.rename({"longitude": "lon", "latitude": "lat"})
    
    # Adjust longitudes to 0-360 if they are now from -180 to 180
    if ds.lon.min() < 0:
        ds = ds.assign_coords(lon=((ds.lon + 360) % 360)).sortby('lon')


    # Ensure time is decoded
    if not np.issubdtype(ds.time.dtype, np.datetime64):
        ds["time"] = xr.decode_cf(ds).time

    # Hour-of-day (works for 30-min or 1-h data)
    hours = ds["time"].dt.hour 
    ds = ds.assign_coords(hour_of_day=("time", hours.data))

    return ds


def shift_diurnal_to_local_time(da, hour_dim="hour_of_day", lon_dim="lon"):
    """
    Shift diurnal cycle data from UTC to local solar time based on longitude.
    Supports both hourly (24 steps) and half-hourly (48 steps) data.
    Works for DataArray with shape (month, hour_of_day, lat, lon).
    Returns a DataArray with a new coordinate 'hour_of_day' (local time).
    """
    nsteps = da[hour_dim].size
    deg_per_step = 360 / nsteps
    # e.g. (360 degrees / 24 hours = 15 degrees per hour)
    lons = da[lon_dim].values
    shifted = da.copy(deep=True)
    # full, independent copy of the data is made, not just a reference to the original data.

    for i, lon in enumerate(lons):
        shift = int(np.round(lon / deg_per_step))
        shifted.loc[{lon_dim: lon}] = da.roll({hour_dim: shift}, roll_coords=False).loc[{lon_dim: lon}]
        # assigns the shifted data for this longitude back into the corresponding longitude slice of the shifted DataArray.
    return shifted


def compute_diurnal_mean(ds, var="hcc"):
    """Compute diurnal cycle for one dataset."""
    
    diurnal = ds[var].groupby("hour_of_day").mean("time")
    # sort hours
    return diurnal.sortby("hour_of_day")


def build_diurnal_climatology(
        dataset_name,
        input_root,
        output_file,
):
    input_root = Path(input_root)
    year = 2018
    monthly_clims = []
    ds = xr.open_dataset(input_root)
    if dataset_name == "HCC":
        ds = ds.sel(threshold=[0.36])
        ds = ds.squeeze('threshold')

    print(f"\n=== Building climatology for {dataset_name} ===")

    for month in range(1, 13):
        mm = f"{month:02d}"
        print(f"\n--- Processing month {mm} ---")
        
        ds_month = ds.sel(time=ds.time.dt.month == month)

        ds_month = load_and_process_single_file(ds_month)

        # Compute year-specific diurnal mean
        diurnal = compute_diurnal_mean(ds_month, var="hcc")

        clim_month = diurnal.expand_dims(month=[month])

        monthly_clims.append(clim_month)

    if not monthly_clims:
        print("No monthly climatologies found — output will not be saved.")
        return

    # Combine all 12 months along a "month" dimension
    final = xr.concat(monthly_clims, dim="month")

    # Only keep the local time shifted version as 'hcc'
    #varname = list(final.data_vars)[0]
    lon_dim = 'longitude' if 'longitude' in final.dims else 'lon'
    hour_dim = 'hour_of_day'
    
    #hcc_local = shift_diurnal_to_local_time(final, hour_dim=hour_dim, lon_dim=lon_dim)
    # we decided to keep the UTC version for climatology files, and convert later
    hcc_local = final

    # Remove all variables, keep only the shifted one as 'hcc'
    final = hcc_local.to_dataset(name='hcc')
    if 'threshold' in final.dims:
        final = final.squeeze('threshold')

    # Remove file if it is already there
    if Path(output_file).exists():
        print(f"  NOTE: Output file {output_file} exists, removing.")
        os.remove(output_file)

    # Save output
    print(f"\n=== Saving final climatology → {output_file} ===")
    final.to_netcdf(output_file)

    print("Done.")


if __name__ == "__main__":
    
    # Example for ccic
    build_diurnal_climatology(
        dataset_name="HCC",
        input_root="/scratch/leko/HCC/hcc_2018_all.nc",
        output_file="/scratch/leko/HCC/HCC_diurnal_climatology_2018_2023_utc.nc",
    )
    
    # # Example for era5
    # build_diurnal_climatology(
    #     dataset_name="ERA5 HCC",
    #     input_root="/scratch/leko/HCC/ERA5/ERA5_1_deg_diurnal/2018/2018_ERA5_diurnal.nc",
    #     output_file="/scratch/leko/HCC/ERA5/ERA5_1_deg_diurnal/2018/ERA5_hcc_diurnal_climatology_2018_utc.nc",
    # )
    

    
    