#!/usr/bin/env bash

# This script performs a conservative remapping on all IMERG data. It also
# merges all files from the same day into one.
#
# Author: Nils Müller
# E-Mail: nils.n.mueller@gmail.com

set -euo pipefail

data_folder=$IMERG_DATA_FOLDER/IMERG_1_deg
mkdir -p $data_folder

if [ ! -f $TARGET_GRID ]
then
    echo "Target-grid description not found '$TARGET_GRID' -> Fail"
    exit 1
fi

for raw_year_folder in ${IMERG_RAW_FOLDERS[@]}
do
    year=$(echo "$raw_year_folder" | awk 'match($0, /[0-9]{4}/) { print substr($0, RSTART, 4) }')
    echo $year
    out_year_folder=$data_folder/$year
    mkdir -p $out_year_folder

    for day in $(ls $raw_year_folder | grep 'IMERG\.[0-9]\{8\}' | sed -n 's/.*IMERG.\([0-9]\{8\}\).*/\1/p' | sort -u)
    do
        echo "Processing day: $day"
        # All files belonging to that day
        src_files=$raw_year_folder/3B-HHR.MS.MRG.3IMERG.${day}*.nc4
        out_file=$out_year_folder/${day}.nc

        if [ -f $out_file ]; then continue; fi

        cdo -s -remapcon,$TARGET_GRID -mergetime $src_files $out_file &
        if (( $(jobs -rp | wc -l) >= NUM_PROCS )); then
            wait -n   # wait for *one* job to finish (bash 5+)
        fi
    done
done
