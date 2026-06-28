#!/usr/bin/env python3

import xarray as xr
from pathlib import Path
import calendar


# Downloads from Google Analysis-Ready, Cloud Optimized ERA5
# https://github.com/google-research/arco-era5?tab=readme-ov-file

# Function to download and save RAW ERA5 data (no diurnal averaging)

def save_monthly_raw_era5(year: int, month: int, variables_to_select, input_base_dir, output_base_dir, var_name):
    '''
    Downloads and saves the raw ERA5 data for the given year and month.
    '''
    ds = xr.open_zarr(
        input_base_dir,
        chunks='auto',
        storage_options=dict(token='anon'),
        decode_timedelta=True,
    )
    
    _, last_day = calendar.monthrange(year, month)
    ds_sel = ds.sel(time=slice(f"{year}-{month}-01", f"{year}-{month}-{last_day}"))
    ds_sel = ds_sel[variables_to_select]
    output_dir = Path(f"{output_base_dir}/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{year}_{month:02d}_era5_raw_{var_name}.nc"
    ds_sel.to_netcdf(out_path)
    print(f"Saved raw ERA5 data to {out_path}")

# Download and save RAW ERA5 data for all months and years from 2018 to 2023
input_base_dir = 'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'

#variables_to_select = ['total_precipitation']  # Change as needed
#output_base_dir = "/scratch/leko/ERA5/precip/ERA5_raw"
#var_name = "tp"

#variables_to_select = ['total_column_cloud_ice_water', 'total_column_snow_water']
#output_base_dir = "/scratch/leko/ERA5/TIWP/ERA5_raw"
#var_name = "tiwp"

input_base_dir = 'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'
variables_to_select = ['high_cloud_cover']
output_base_dir = "/scratch/leko/ERA5/HCC/ERA5_hcc_raw/"
var_name = "hcc"

for year in range(2018, 2019):
    for month in range(1, 13):
        try:
            save_monthly_raw_era5(year, month, variables_to_select,input_base_dir, output_base_dir, var_name)
        except Exception as e:
            print(f"Failed for {year}-{month}: {e}")

# %% Already diurnaly averaged (here done only for ERA5 TIWP during Lara's master thesis, 
# commented out for other two variables because that was done in store_diurnal_monthly)
'''
def get_monthly_tiwp_average_era5(
        year: int, 
        month: int,
        variables_to_select
        ) -> xr.Dataset:
    
    
    # Calculates the 'average day' of the field for a given month and year.
    # The end result is a dataset with 24 hours.

    
    
    ds = xr.open_zarr(
    'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3',
    chunks='auto',
    storage_options=dict(token='anon'),
    )
    # select year and month 
    _, last_day = calendar.monthrange(year, month)
    ds_sel = ds.sel(time = slice(f"{year}-{month}-01", f"{year}-{month}-{last_day}"))
    ds_sel = ds_sel[variables_to_select]
    # I don't need to filter for era5
    #threshold = 40
    #ds_filtered = ds_sel.where(~np.isnan(ds_sel) & (ds_sel.total_column_cloud_ice_water <= threshold) & (ds_sel.total_column_snow_water <= threshold))
    ds_filtered = ds_sel.groupby(ds_sel.time.dt.hour).mean() 

    return ds_filtered

for year in range(2023, 2024):            
    for month in range(1, 13):
            try:
                ds_tiwp_mean = get_monthly_tiwp_average_era5(year, month,variables_to_select)
                # This is where the folder originaly was, change this to somewhere else
                output_dir = Path(f"/scratch/leko/ERA5_precipitation/{year}")
                output_dir.mkdir(parents=True, exist_ok=True)
                ds_tiwp_mean.to_netcdf(output_dir / f"{year}_{month:02d}_era5_mean_tiwp.nc")
            except Exception as e:
                print(f"Failed for {year}-{month}: {e}")
'''