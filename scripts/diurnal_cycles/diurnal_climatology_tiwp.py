#!/usr/bin/env python3
###############################################################################################################
# Script to compute diurnal climatologies from monthly ERA5 , CCIC and DYAMOND FWP data for the full study period
# Data can be stored in utc or local solar time.


import os
import xarray as xr
import numpy as np
from pathlib import Path


def load_and_process_single_file(infile, dataset_name, half_hourly = False, varname_out="tiwp"):
    """Open one file, detect variable name, rename, compute hour-of-day coordinate."""
    ds = xr.open_dataset(infile, decode_timedelta=True)

    ds = ds.rename({"longitude": "lon", "latitude": "lat"})
        # Adjust longitudes to 0-360 if they are now from -180 to 180
    if ds.lon.min() < 0:
        ds = ds.assign_coords(lon=((ds.lon + 360) % 360)).sortby('lon')

    if dataset_name == "CCIC_TIWP":
        # Detect variable name
        if "tiwp_stratified" in ds:
            var = "tiwp_stratified"
        else:
            raise ValueError(f"Cannot find tiwp variable in {infile}")
        # Rename to unified name
        ds = ds.where(ds[var]>=0)
        ds = ds.rename({var: varname_out})
        da_hourly = ds

        if not half_hourly:
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
            raise ValueError(f"Cannot find tiwp variable in {infile}")
    return da_hourly

def shift_diurnal_to_local_time(da, hour_dim="hour_of_day", lon_dim="lon"):
    """
    Shift diurnal cycle data from UTC to local solar time based on longitude.
    Supports both hourly (24 steps) and half-hourly (48 steps) data.
    Works for DataArray with shape (month, hour_of_day, lat, lon).
    Returns a DataArray with a new coordinate 'hour_of_day' (local time).

    I learned it it better to store data in UTC and shift it later.
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


def build_diurnal_climatology(
        dataset_name,
        input_root,
        output_file,
        start_year,
        end_year,
        monthly_pattern,
        half_hourly,
        utc
):
    input_root = Path(input_root)

    monthly_clims = []

    print(f"\n=== Building climatology for {dataset_name} ===")

    for month in range(1, 13):
        mm = f"{month:02d}"
        print(f"\n--- Processing month {mm} ---")

        yearly_diurnals = []

        for year in range(start_year, end_year + 1):
            yr = str(year)

            # Files
            f1 = input_root / yr / monthly_pattern.format(year=yr, month=mm)

            if f1.exists():
                infile = f1
            else:
                print(f"  WARNING: No file for {year}-{mm}. {f1} not found.")
                continue

            print(f"  Using {infile.name}")

            diurnal = load_and_process_single_file(infile, dataset_name, half_hourly=half_hourly)

            # Compute year-specific diurnal mean
            
            diurnal = diurnal.expand_dims(year=[year])
            yearly_diurnals.append(diurnal)

        if not yearly_diurnals:
            print(f"  No data for month {mm}, skipping.")
            continue

        # Stack all years (set join explicitly)
        ds_month = xr.concat(yearly_diurnals, dim="year", join="outer")

        # Convert to climatological mean
        clim_month = ds_month.mean("year")
        # Ensure we don't try to expand a dimension that already exists
        if "month" in clim_month.dims:
            # If a month dimension exists, select the first entry to collapse it
            clim_month = clim_month.isel(month=0)
        clim_month = clim_month.expand_dims(month=[month])

        monthly_clims.append(clim_month)

    if not monthly_clims:
        print("No monthly climatologies found — output will not be saved.")
        return

    # Combine all 12 months along a "month" dimension
    final = xr.concat(monthly_clims, dim="month")

    
    lon_dim = 'lon'
    hour_dim = 'hour_of_day'
    if utc:
        print("\n=== Keeping diurnal cycle in UTC time ===")
        tiwp_local = final
        output_file = output_file.replace(".nc", "_utc.nc")
    else:
        print("\n=== Shifting diurnal cycle to local solar time ===")
        tiwp_local = shift_diurnal_to_local_time(final, hour_dim=hour_dim, lon_dim=lon_dim)
        # Remove all variables, keep only the shifted one as 'tiwp'
        final = tiwp_local.to_dataset(name='tiwp')

    if half_hourly:
        output_file = output_file.replace(".nc", "_30min.nc")
    # Remove file if it is already there
    if Path(output_file).exists():
        print(f"  NOTE: Output file {output_file} exists, removing.")
        os.remove(output_file)

    # Save output
    print(f"\n=== Saving final climatology → {output_file} ===")
    final.to_netcdf(output_file)

    print("Done.")


if __name__ == "__main__":
    '''
    
    # Example for ERA5
    build_diurnal_climatology(
        dataset_name="ERA5",
        input_root="/data/s5/users/lara/master_thesis/data/ERA5/diurnal_data",
        output_file="/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_climatology_2018_2023.nc",
        start_year=2018,
        end_year=2023,
        monthly_pattern="{year}_{month}_era5_mean_1deg.nc",
        half_hourly=False,
        # Attention here:
        utc=True
    )

    '''
    # Example for CCIC CPCIR TIWP
    build_diurnal_climatology(
        dataset_name="CCIC_TIWP",
        input_root="/data/s5/users/lara/master_thesis/data/ccic/diurnal_data",
        output_file="/data/s5/users/lara/master_thesis/data/ccic/CCIC_TIWP_diurnal_climatology_2018_2023.nc",
        start_year=2018,
        end_year=2023,
        monthly_pattern="ccic_cpcir_{year}_{month}_monthlymean_1deg_tiwp.nc",
        half_hourly=False,
        # Attention here:
        utc=True
    )
    
    