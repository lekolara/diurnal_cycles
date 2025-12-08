#!/usr/bin/env bash
set -euo pipefail

NUM_PROCS=64
BASE="/scratch/leko"
RAW_BASE=$BASE/ERA5/ERA5_raw
OUT_BASE=$BASE/ERA5/ERA5_1_deg
GRID_FILE=$BASE/ERA5/ERA5_grid.txt
TARGET_GRID=$BASE/IMERG/GPM_IMERG_1_deg/grid_1deg.txt

mkdir -p "$OUT_BASE"

if [ ! -f $TARGET_GRID ]
then
    echo "Target-grid description not found '$TARGET_GRID' -> Fail"
    exit 1
fi


for relative_year_dir in $(ls $RAW_BASE)
do
    year=${relative_year_dir}
    echo $year
    raw_year_folder=$RAW_BASE/$relative_year_dir
    out_year_folder=$OUT_BASE/$year
    mkdir -p $out_year_folder

    for file in "$raw_year_folder"/*.nc
    do
        filename=$(basename "$file")
        month=${filename:5:2}   # extract 01,02,...,12
        out_file="$out_year_folder/${year}${month}.nc"

        if [ ! -f "$out_file" ]; then
            echo "Regridding: $filename → $out_file"
            cdo -s -remapcon,"$TARGET_GRID" "$file" "$out_file" &
        fi

        # limit parallel jobs
        if (( $(jobs -rp | wc -l) >= NUM_PROCS )); then
            wait -n
        fi
    done
done

wait   # wait for all remaining jobs
