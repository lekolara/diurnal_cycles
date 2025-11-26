#!/usr/bin/env bash
set -euo pipefail

#IMERG
#INPUT_BASE="/scratch/leko/IMERG/IMERG_1_deg"          
#OUTPUT_ROOT="/scratch/leko/IMERG/IMERG_1_deg_diurnal"
#DATASET="IMERG"
#DATASET_TYPE="daily"      # daily or monthly

#ERA5
# Input base directory (your ERA5 data)
INPUT_BASE="/scratch/leko/ERA5/ERA5_1_deg"
# Output directory where diurnal averages will be stored
OUTPUT_ROOT="/scratch/leko/ERA5/ERA5_1_deg_diurnal"
DATASET="ERA5"
DATASET_TYPE="monthly"    # daily or monthly

START_YEAR=2018
END_YEAR=2023

for (( year=${START_YEAR}; year<=${END_YEAR}; year++ )); do
    
    echo "=== Processing year ${year} ==="

    YEAR_IN="${INPUT_BASE}/${year}"
    YEAR_OUT="${OUTPUT_ROOT}/${year}"
    mkdir -p "${YEAR_OUT}"

    for month in {01..12}; do
        echo "--- Processing month ${month} ---"

        # DEFAULT output path
        monthly_input="${YEAR_OUT}/${year}_${month}_merged.nc"
        outfile="${YEAR_OUT}/${year}_${month}_${DATASET}_diurnal_mean.nc"

        if [ "${DATASET_TYPE}" = "monthly" ]; then
            # try 2018_01.nc or 201801.nc
            f1="${YEAR_IN}/${year}_${month}.nc"
            f2="${YEAR_IN}/${year}${month}.nc"

            if [ -f "${f1}" ]; then
                monthly_input="${f1}"
            elif [ -f "${f2}" ]; then
                monthly_input="${f2}"
            else
                echo "WARNING: No monthly file found for ${year}-${month}"
                continue
            fi

        elif [ "${DATASET_TYPE}" = "daily" ]; then
            # daily files like 20180724.nc
            filelist=$(ls ${YEAR_IN}/${year}${month}??.nc 2>/dev/null || true)

            if [ -z "${filelist}" ]; then
                echo "WARNING: No daily files for ${year}-${month}"
                continue
            fi

            echo "Merging daily files → ${monthly_input}"
            cdo -O mergetime ${filelist} "${monthly_input}"
        fi

        echo "--> Calculating diurnal mean for ${monthly_input}"
        cdo -O dhourmean "${monthly_input}" "${outfile}"

    done
done

echo "=== DONE! Output in: ${OUTPUT_ROOT} ==="
