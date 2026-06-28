#!/usr/bin/env python3
###############################################################################################################
# Script to compute diurnal climatologies from monthly ERA5 , CCIC and DYAMOND precip data for the full study period
# Data can be stored in utc or local solar time.


import os
import xarray as xr
import numpy as np
from pathlib import Path
import pandas as pd


def load_and_process_single_file(filename, varname_out="pr", half_hourly=False, multiply_era5=False):
    """Open one file, detect variable name, rename, compute hour-of-day coordinate."""
    ds = xr.open_dataset(filename)

    # Detect variable name
    if "precipitation" in ds:
        var = "precipitation"
    elif "total_precipitation" in ds:
        var = "total_precipitation"
    else:
        raise ValueError(f"Cannot find precipitation variable in {filename}")

    # Rename to unified name
    ds = ds.where(ds[var]>=0)
    ds = ds.rename({var: varname_out})

    if ds.lon.min() < 0:
        ds = ds.assign_coords(lon=((ds.lon + 360) % 360)).sortby('lon')

    # Multiply by 1000 for ERA5 if requested 
    if multiply_era5:
        ds[varname_out] = ds[varname_out] * 1000
    
    # Ensure time is decoded
    if not np.issubdtype(ds.time.dtype, np.datetime64):
        ds["time"] = xr.decode_cf(ds).time

    # Hour-of-day (works for 30-min or 1-h data)

    if half_hourly:
    
        half_hours = pd.to_timedelta(ds['time'].dt.hour, unit='h') + pd.to_timedelta(ds['time'].dt.minute, unit='m')
        ds = ds.assign_coords(hour_of_day=("time", half_hours))
    else:
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


def compute_diurnal_mean(ds, var="pr"):
    """Compute diurnal cycle for one dataset."""
    
    diurnal = ds[var].groupby("hour_of_day").mean("time")
    # sort hours
    return diurnal.sortby("hour_of_day")


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

            # File candidates
            f1 = input_root / yr / monthly_pattern.format(year=yr, month=mm)

            if f1.exists():
                infile = f1
            else:
                print(f"  WARNING: No file for {year}-{mm}")
                continue

            print(f"  Using {infile.name}")


            # Load + rename + add hour_of_day
            multiply_era5 = dataset_name.upper() == "ERA5"
            ds = load_and_process_single_file(infile, half_hourly=half_hourly, multiply_era5=multiply_era5)

            # Compute year-specific diurnal mean
            diurnal = compute_diurnal_mean(ds)
            diurnal = diurnal.expand_dims(year=[year])
            yearly_diurnals.append(diurnal)

        if not yearly_diurnals:
            print(f"  No data for month {mm}, skipping.")
            continue

        # Stack all years
        ds_month = xr.concat(yearly_diurnals, dim="year")

        # Convert to climatological mean
        clim_month = ds_month.mean("year")
        clim_month = clim_month.expand_dims(month=[month])

        monthly_clims.append(clim_month)

    if not monthly_clims:
        print("No monthly climatologies found — output will not be saved.")
        return

    # Combine all 12 months along a "month" dimension
    final = xr.concat(monthly_clims, dim="month")

    # Only keep the local time shifted version as 'pr'
    #varname = list(final.data_vars)[0]
    lon_dim = 'lon'
    hour_dim = 'hour_of_day'

    if utc:
        pr_local = final
        output_file = output_file.replace(".nc", "_utc.nc")
    else:
        pr_local = shift_diurnal_to_local_time(final, hour_dim=hour_dim, lon_dim=lon_dim)
        # we decided to keep the UTC version for climatology files, and convert later
        # # Remove all variables, keep only the shifted one as 'pr'
    final = pr_local.to_dataset(name='pr')

    if half_hourly:
        output_file = output_file.replace(".nc", "_30min.nc")

    # Reorder dimensions to (month, hour_of_day, lat, lon)
    final = final.transpose("month", "hour_of_day", "lat", "lon")

    # Remove file if it is already there
    if Path(output_file).exists():
        print(f"  NOTE: Output file {output_file} exists, removing.")
        os.remove(output_file)

    # Fix crash: remove problematic CF-time bounds if present
    if "time_bnds" in final:
        print("→ Removing time_bnds to avoid encoding error.")
        final = final.drop_vars("time_bnds")

    # Save output
    print(f"\n=== Saving final climatology → {output_file} ===")
    final.to_netcdf(output_file)

    print("Done.")


if __name__ == "__main__":
    '''
    
    # Example for ERA5
    build_diurnal_climatology(
        dataset_name="ERA5",
        input_root="/scratch/leko/ERA5/precip/ERA5_1_deg_diurnal/diurnal_data",
        output_file="/scratch/leko/ERA5/precip/ERA5_1_deg_diurnal/ERA5_diurnal_climatology_2018_2023.nc",
        start_year=2018,
        end_year=2023,
        monthly_pattern="{year}_{month}_ERA5_diurnal_mean.nc",
        half_hourly=False,
        utc=True
    )
    
    '''
    # Example for IMERG 
    build_diurnal_climatology(
        dataset_name="IMERG",
        input_root="/scratch/leko/IMERG/IMERG_1_deg_diurnal/diurnal_data/",
        output_file="/scratch/leko/IMERG/IMERG_1_deg_diurnal/IMERG_diurnal_climatology_2018_2023.nc",
        start_year=2018,
        end_year=2023,
        monthly_pattern="{year}_{month}_IMERG_diurnal_mean.nc",
        half_hourly=False,
        utc=True
    )
    
    
    

    
    