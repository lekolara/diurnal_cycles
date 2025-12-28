#!/usr/bin/env python3

import xarray as xr
import glob
import os

DYAMOND_DIR = "/scratch/nilsmu/DYAMOND_precipitation/data/latlon_grid_1deg"
IMERG_DIR   = "/scratch/leko/IMERG/IMERG_1_deg"
ERA5_DIR    = "/scratch/leko/ERA5/ERA5_1_deg"
OUTPUT_DIR  = "/scratch/leko/zonal_means/feb"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def zonal_mean(files, var_in, var_out, multiply=None):
    """Compute zonal mean-only using xarray."""
    if len(files) == 0:
        print("No files found.")
        return None

    ds = xr.open_mfdataset(files, combine='by_coords')

    # select the variable
    ds = ds.where(ds[var_in]>=0)
    da = ds[var_in]

    # scale if needed (ERA5)
    if multiply is not None:
        da = da * multiply

    # time mean
    da = da.mean("time")

    # zonal mean (avg over longitudes)
    # try common names
    for lon_name in ["lon", "longitude"]:
        if lon_name in da.dims:
            da = da.mean(lon_name)
            break

    # rename variable
    da = da.rename(var_out)

    return da


#########################################
# DYAMOND models
#########################################
DYAMOND_MODEL_NAMES = ["ARPEGE", "GEOS", "gSAM", "ICON", "IFS", "SHiELD"]
DYAMOND_MODEL_NAMES = ['IFS']
for model in DYAMOND_MODEL_NAMES:
    files = glob.glob(f"{DYAMOND_DIR}/{model}/*.nc")
    out_file = f"{OUTPUT_DIR}/{model}.nc"

    #if os.path.exists(out_file):
   #     continue

    # Delete old output file if exists
    if os.path.exists(out_file):
        os.remove(out_file)

    da = zonal_mean(files, var_in="pr", var_out="pr")

    if da is not None:
        da.to_netcdf(out_file)
        print("Saved", out_file)

'''
#########################################
# IMERG
#########################################
files = glob.glob(f"{IMERG_DIR}/20??/20??02*.nc")
out_file = f"{OUTPUT_DIR}/IMERG.nc"

if os.path.exists(out_file):
    os.remove(out_file)

if not os.path.exists(out_file):
    da = zonal_mean(files, var_in="precipitation", var_out="pr")
    if da is not None:
        da.to_netcdf(out_file)
        print("Saved", out_file)


#########################################
# ERA5
#########################################
files = glob.glob(f"{ERA5_DIR}/*/*_02.nc")
out_file = f"{OUTPUT_DIR}/ERA5.nc"


if os.path.exists(out_file):
    os.remove(out_file)

if not os.path.exists(out_file):
    da = zonal_mean(files, var_in="total_precipitation",
                    var_out="pr", multiply=1000)
    if da is not None:
        da.to_netcdf(out_file)
        print("Saved", out_file)

'''