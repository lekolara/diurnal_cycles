#!/usr/bin/env python3
import numpy as np
from pathlib import Path
import xarray as xr
# gSAM precipitation is stored as cumulative values, but we want instantaneous rates. 
in_dir  = Path("/scratch/leko/DYAMOND_PRECIP/data/latlon_grid_1deg/gSAM/gSAM_accumulated")    # old GSAM folder
out_dir = Path("/scratch/leko/DYAMOND_PRECIP/data/latlon_grid_1deg/gSAM/")

var = "pr"   # precipitation variable name

out_dir.mkdir(parents=True, exist_ok=True)

# -------- PROCESS FILES --------
files = sorted(in_dir.glob("*.nc"))
print(f"Found {len(files)} GSAM files")

for f in files:
    print(f"Processing {f.name}")

    ds = xr.open_dataset(f)

    # time-difference to convert cumulative → instantaneous rate
    dp = ds[var].diff("time", label="lower")


    # Copy metadata
    dp.attrs = ds[var].attrs.copy()
    dp.attrs["long_name"] = "surface precipitation rate (corrected from cumulative)"
    dp.attrs["standard_name"] = "precipitation_flux"
    dp.attrs["units"] = "mm h-1"
    dp.attrs["processing_note"] = "Converted from cumulative precipitation using time differencing"

    # Create output dataset
    out_ds = dp.to_dataset(name=var)

    # Preserve global attrs
    out_ds.attrs = ds.attrs.copy()
    out_ds.attrs["postprocessing"] = "GSAM cumulative precipitation converted to rate using xr.diff(time)"

    # Save
    out_file = out_dir / f.name
    out_ds.to_netcdf(out_file)

    ds.close()
    out_ds.close()

print("GSAM correction finished.")
