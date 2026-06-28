#!/usr/bin/env python3
import numpy as np
from pathlib import Path
import xarray as xr

# The way xr.diff works is that the output array has one less time step.
# -------- CONFIG --------
in_dir  = Path("/scratch/leko/DYAMOND_PRECIP/data/latlon_grid_1deg/IFS/IFS_accumulated")    # old IFS folder
out_dir = Path("/scratch/leko/DYAMOND_PRECIP/data/latlon_grid_1deg/IFS/")

var = "pr"   # precipitation variable name

out_dir.mkdir(parents=True, exist_ok=True)

# -------- PROCESS FILES --------
files = sorted(in_dir.glob("*.nc"))
print(f"Found {len(files)} IFS files")

for i, f in enumerate(files):
    print(f"Processing {f.name}")

    ds = xr.open_dataset(f)

    # time-difference to convert cumulative → instantaneous rate
    dp = ds[var].diff("time", label="lower")
    p = ds[var]
    # Move time coordinate back to start at 0:00


    # try to get next file's first timestep to compute 23->00
    if i + 1 < len(files):
        ds_next = xr.open_dataset(files[i+1])
        p_next0 = ds_next[var].isel(time=0)
        ds_next.close()

        last = p_next0 - p.isel(time=-1)
        # attach correct time (the 00:00 timestamp belongs to next day, but
        # you usually want to keep it as the current day's 00:00 slot or
        # attach to the last slot as appropriate)
        last = last.expand_dims(time=[p.time.values[-1]])  # use current file's 23:00 label
        # concat to restore full 24 values
        dp = xr.concat([dp, last], dim="time")

    else:
        # no next file available: you can either
        # - leave dp as is (23->00 missing), or
        # - fill with NaN (keeps length 24)
        last = xr.full_like(p.isel(time=0), np.nan)
        last = last.expand_dims(time=[p.time.values[-1]])
        dp = xr.concat([dp, last], dim="time")

    # Copy metadata
    dp.attrs = ds[var].attrs.copy()
    dp.attrs["long_name"] = "surface precipitation rate (corrected from cumulative)"
    dp.attrs["standard_name"] = "precipitation_flux"
    dp.attrs["units"] = "mm h-1"
    dp.attrs["processing_note"] = "Converted from cumulative precipitation using time differencing and m-to-mm conversion"

    # Create output dataset
    out_ds = dp.to_dataset(name=var)*1000  # convert from m to mm
    
    # Preserve global attrs
    out_ds.attrs = ds.attrs.copy()
    out_ds.attrs["postprocessing"] = "IFS cumulative precipitation converted to rate using xr.diff(time) and m-to-mm conversion"
    # Save
    out_file = out_dir / f.name
    out_ds.to_netcdf(out_file)

    ds.close()
    out_ds.close()

print("IFS correction finished.")
