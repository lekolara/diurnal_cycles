#!/usr/bin/env python3

import xarray as xr
from pathlib import Path
# import nest_asyncio
# nest_asyncio.apply()
# import asyncio
# try:
#     asyncio.get_running_loop()
# except RuntimeError:
#     asyncio.set_event_loop(asyncio.new_event_loop())



# Downloads from Google Analysis-Ready, Cloud Optimized ERA5
# https://github.com/google-research/arco-era5?tab=readme-ov-file

# Function to download and save RAW ERA5 data (no diurnal averaging)

def save_monthly_raw_era5(year: int, month: int, variables_to_select, input_base_dir, output_base_dir):
    '''
    Downloads and saves the raw ERA5 data for the given year and month (no averaging).
    '''
    ds = xr.open_zarr(
        input_base_dir,
        chunks='auto',
        storage_options=dict(token='anon'),
        decode_timedelta=True,
    )
    import calendar
    _, last_day = calendar.monthrange(year, month)
    ds_sel = ds.sel(time=slice(f"{year}-{month}-01", f"{year}-{month}-{last_day}"))
    ds_sel = ds_sel[variables_to_select]
    output_dir = Path(f"{output_base_dir}/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{year}_{month:02d}_era5_raw.nc"
    ds_sel.to_netcdf(out_path)
    print(f"Saved raw ERA5 data to {out_path}")

# Download and save RAW ERA5 data for all months and years from 2018 to 2023
#variables_to_select = ['total_precipitation']  # Change as needed
#variables_to_select = ['total_column_cloud_ice_water', 'total_column_snow_water']
input_base_dir = 'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'

#output_base_dir = "/scratch/leko/ERA5_raw"
#output_base_dir = "/scratch/leko/TIWP/ERA5/ERA5_raw"

variables_to_select = ["hcc"]
input_base_dir = 'gs://gcp-public-data-arco-era5/co/single-level-reanalysis.zarr-v2'
output_base_dir = "/scratch/leko/HCC/ERA5/ERA5_hcc_raw/regular_grid_0.25"

input_base_dir = 'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'
variables_to_select = ['high_cloud_cover']


for year in range(2018, 2019):
    for month in range(1, 13):
        try:
            save_monthly_raw_era5(year, month, variables_to_select,input_base_dir, output_base_dir)
        except Exception as e:
            print(f"Failed for {year}-{month}: {e}")