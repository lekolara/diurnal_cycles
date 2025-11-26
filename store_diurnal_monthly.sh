#!/usr/bin/env bash
set -euo pipefail


# ERA5
# Input base directory (your ERA5 data)
#INPUT_BASE="/scratch/leko/ERA5/ERA5_1_deg"
# Output directory where diurnal averages will be stored
#OUTPUT_ROOT="/scratch/leko/ERA5/ERA5_1_deg_diurnal"
#DATASET = "ERA5"


#IMERG
INPUT_BASE="/scratch/leko/IMERG/IMERG_1_deg"          
OUTPUT_ROOT="/scratch/leko/IMERG/IMERG_1_deg_diurnal"
DATASET="IMERG"

# DYAMOND

#INPUT_BASE="/scratch/nilsmu/DYAMOND_precipitation/data/latlon_grid_1deg"

# Years you want to process
START_YEAR=2018
END_YEAR=2023

# Loop over years
for (( year=${START_YEAR}; year<=${END_YEAR}; year++ )); do
    
    echo "=== Processing year ${year} ==="

    # Path to the folder with monthly files
    YEAR_IN="${INPUT_BASE}/${year}"

    # Output folder for this year
    YEAR_OUT="${OUTPUT_ROOT}/${year}"
    mkdir -p "${YEAR_OUT}"

    # Loop over months 01..12
    for month in {01..12}; do

        # --- Try first naming pattern: 2018_01.nc ---
        f1="${YEAR_IN}/${year}_${month}.nc"

        # --- Try second naming pattern: 201801.nc ---
        f2="${YEAR_IN}/${year}${month}.nc"

        # Pick whichever exists
        if [ -f "${f1}" ]; then
            infile="${f1}"
        elif [ -f "${f2}" ]; then
            infile="${f2}"
        else
            echo "WARNING: No file found for ${year}-${month} (checked: ${f1}, ${f2})"
            continue
        fi
        
        echo "--> Creating diurnal cycle for ${infile}"

        # The correct CDO operator is dhourmean (NOT dihourmean)
        cdo -O dhourmean "${infile}" "${outfile}"
    done
done

echo "=== DONE! All diurnal files stored under: ${OUTPUT_ROOT} ==="
