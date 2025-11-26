#!/usr/bin/env python3

import xarray as xr
import glob
import os


IMERG_DIR   = "/scratch/leko/IMERG/IMERG_1_deg"
ERA5_DIR    = "/scratch/leko/ERA5/ERA5_1_deg"
OUTPUT_DIR  = "/scratch/leko/zonal_means/all_months"

os.makedirs(OUTPUT_DIR, exist_ok=True)



def zonal_mean(files, var_in, var_out, multiply=None):
    """Compute zonal mean-only using xarray."""
    if len(files) == 0:
        print("  No files found for this month.")
        return None
    try:
        ds = xr.open_mfdataset(files, combine='by_coords')
        da = ds[var_in]
        if multiply is not None:
            da = da * multiply
        # time mean
        da = da.mean("time")
        # zonal mean (avg over longitudes)
        for lon_name in ["lon", "longitude"]:
            if lon_name in da.dims:
                da = da.mean(lon_name)
                break
        da = da.rename(var_out)
        return da
    except Exception as e:
        print(f"  Error processing files: {files[:2]}... ({len(files)} files). Error: {e}")
        return None

def monthly_zonal_means(years, months, file_pattern, var_in, var_out, multiply=None):
    """Compute zonal means for each month and stack into a DataArray with 'month' dimension."""
    results = []
    valid_months = []
    for month in months:
        print(f"Processing month {month:02d}...")
        files = []
        for year in years:
            pattern = file_pattern.format(year=year, month=str(month).zfill(2))
            found = glob.glob(pattern)
            if found:
                print(f"  Found {len(found)} files for {year}-{month:02d}")
            files += found
        if not files:
            print(f"  No files found for month {month:02d} in any year.")
        da = zonal_mean(files, var_in, var_out, multiply=multiply)
        if da is not None:
            results.append(da)
            valid_months.append(month)
    if results:
        print(f"Concatenating {len(results)} months...")
        stacked = xr.concat(results, dim="month")
        stacked = stacked.assign_coords(month=("month", valid_months))
        return stacked
    else:
        print("No valid data to concatenate.")
        return None




#########################################
# IMERG (2018-2023, all months)
#########################################
years = range(2018, 2024)
months = range(1, 13)
imerg_pattern = f"{IMERG_DIR}/{{year}}/{{year}}{{month}}*.nc"
out_file = f"{OUTPUT_DIR}/IMERG_monthly.nc"

if not os.path.exists(out_file):
    print(f"Starting IMERG zonal mean calculation. Output: {out_file}")
    da = monthly_zonal_means(years, months, imerg_pattern, var_in="precipitation", var_out="pr")
    if da is not None:
        try:
            da.to_netcdf(out_file)
            print("Saved", out_file)
        except Exception as e:
            print(f"Error saving NetCDF file: {e}")
    else:
        print("No data to save for IMERG.")


'''
#########################################
# ERA5 (2018-2023, all months)
#########################################
era5_pattern = f"{ERA5_DIR}/{{year}}/*_{{month}}.nc"
out_file = f"{OUTPUT_DIR}/ERA5_monthly.nc"

if not os.path.exists(out_file):
    da = monthly_zonal_means(years, months, era5_pattern, var_in="total_precipitation", var_out="pr", multiply=1000)
    if da is not None:
        da.to_netcdf(out_file)
        print("Saved", out_file)
'''