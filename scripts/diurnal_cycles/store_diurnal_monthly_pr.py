#!/usr/bin/env python3

import pandas as pd
import xarray as xr
from pathlib import Path

def build_diurnal_for_dataset(
    dataset_name,
    stored_as,      # "monthly" or "daily"
    var_in,
    var_out,
    resolution,
    input_root,
    output_root
):
    start_year = 2018
    end_year = 2018

    input_root = Path(input_root)
    output_root = Path(output_root)

    for year in range(start_year, end_year + 1):
        print(f"\n=== Processing year {year} ===")

        year_in = input_root / str(year)
        year_out = output_root / str(year)
        year_out.mkdir(parents=True, exist_ok=True)

        for month in range(1, 13):
            mstr = f"{month:02d}"
            print(f"--- Processing month {mstr} ---")

            # -----------------------------
            # LOAD MONTHLY DATA
            # -----------------------------

            if stored_as == "monthly":

                f1 = year_in / f"{year}_{mstr}.nc"
                f2 = year_in / f"{year}{mstr}.nc"

                infile = f1 if f1.exists() else f2 if f2.exists() else None

                if infile is None:
                    print("  WARNING: No input file found")
                    continue

                ds = xr.open_dataset(infile)

            elif stored_as == "daily":
                daily_files = sorted(year_in.glob(f"{year}{mstr}??.nc"))

                if not daily_files:
                    print("  WARNING: No daily files")
                    continue

                ds = xr.open_mfdataset(
                    daily_files,
                    combine="nested",
                    concat_dim="time"
                )

            else:
                raise ValueError("dataset_type must be monthly or daily")


            # -----------------------------
            # SELECT AND RENAME VARIABLE
            # -----------------------------

            if var_in not in ds:
                raise KeyError(f"{var_in} not found in {infile}")

            ds = ds[[var_in]].rename({var_in: var_out})


            # -----------------------------
            # DIURNAL MEAN
            # -----------------------------

            if resolution == "hourly":
                # ERA5 — 24 bins
                ds_out = ds.groupby("time.time").mean(dim="time", skipna=True)
                time_intervals = pd.date_range(start= str(year)+'-'+mstr+'-01 00:00:00', end= str(year)+'-'+mstr+'-01 23:00:00', freq='1H')
                ds_out = ds_out.assign_coords(time= time_intervals)

            else:
                # IMERG — keep 30-min resolution = 48 bins
                ds_out = ds.groupby("time.time").mean(dim="time", skipna=True)
                time_intervals = pd.date_range(start= str(year)+'-'+mstr+'-01 00:00:00', end= str(year)+'-'+mstr+'-01 23:30:00', freq='30T')
                ds_out = ds_out.assign_coords(time= time_intervals)


            # -----------------------------
            # SAVE FILE
            # -----------------------------

            outfile = year_out / f"{year}_{mstr}_{dataset_name}_diurnal_mean.nc"
            ds_out.to_netcdf(outfile)
            print(f"  ✓ Saved → {outfile}")


# -----------------------------
# RUN BOTH DATASETS
# -----------------------------
'''
build_diurnal_for_dataset(
    dataset_name="ERA5",
    stored_as="monthly",
    var_in="total_precipitation",
    var_out="pr",
    resolution="hourly",
    input_root="/scratch/leko/ERA5/ERA5_1_deg",
    output_root="/scratch/leko/ERA5/ERA5_1_deg_diurnal",
)
'''

build_diurnal_for_dataset(
    dataset_name="IMERG",
    stored_as="daily",
    var_in="precipitation",
    var_out="pr",
    resolution="30min",
    input_root="/scratch/leko/IMERG/IMERG_1_deg",
    output_root="/scratch/leko/IMERG/IMERG_1_deg_diurnal_cp",
)
