#!/usr/bin/env bash

############################################################################################################
# Script to calculate diurnal means from monthly ERA5 HCC merge them into a single file per month 
# for every year, in hourly resolution.

set -euo pipefail

#ERA5
# Input base directory
INPUT_BASE="/scratch/leko/ERA5/HCC/ERA5_hcc_1_deg"
# Output directory where diurnal averages will be stored
OUTPUT_ROOT="/scratch/leko/ERA5/HCC/ERA5_1_deg_diurnal"
DATASET="ERA5"

START_YEAR=2018
END_YEAR=2018

for (( year=${START_YEAR}; year<=${END_YEAR}; year++ )); do
    
    echo "=== Processing year ${year} ==="

    YEAR_IN="${INPUT_BASE}/${year}"

    YEAR_OUT="${OUTPUT_ROOT}/${year}"
    mkdir -p "${YEAR_OUT}"

    for month in {01..12}; do
        echo "--- Processing month ${month} ---"

        # DEFAULT output path
    
        outfile="${YEAR_OUT}/${year}_${month}_${DATASET}_diurnal_mean.nc"

        monthly_input="${YEAR_IN}/${year}${month}"

        echo "--> Calculating diurnal mean for ${monthly_input}"
        rm -f "${outfile}"
        #rm -f "${monthly_input}"

        cdo -O dhourmean "${monthly_input}.nc" "${outfile}"
        #rm -f "${monthly_input}.nc"

    done

    merged_out="${YEAR_OUT}/${year}_${DATASET}_diurnal.nc"

    # Remove old file if exists
    rm -f "${merged_out}"

    monthly_files=""
    for m in $(seq -w 1 12); do
        monthly_files="${monthly_files} ${YEAR_OUT}/${year}_${m}_${DATASET}_diurnal_mean.nc"
    done

    # Merge along time dimension
    cdo -O mergetime ${monthly_files} "${merged_out}"

    echo "Created: ${merged_out}"
done

echo "=== DONE! Output in: ${OUTPUT_ROOT} ==="
