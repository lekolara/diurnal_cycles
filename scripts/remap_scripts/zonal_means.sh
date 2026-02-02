#!/usr/bin/env bash

# This script computes the zonal means in February of ERA5, IMERG and DYAMOND.
#
# Author: Nils Müller
# E-Mail: nils.n.mueller@gmail.com

set -euo pipefail
source config.sh

DYAMOND_FOLDER=$DYA_DATA_FOLDER/$(basename -s .txt $TARGET_GRID)
IMERG_FOLDER=$IMERG_DATA_FOLDER/$(basename -s .txt $TARGET_GRID)
OUTPUT_DIR=$DYA_BASE_FOLDER/zonal_means/$(basename -s .txt $TARGET_GRID)

mkdir -p $OUTPUT_DIR

# Zonal means of DYAMOND data
dya_zonmean_files=()
for model in ${DYA_MODEL_NAMES[@]}
do
    folder=$DYAMOND_FOLDER/$model
    files=$folder/*.nc
    mean_file=$OUTPUT_DIR/${model}.nc

    if [ ! -d $folder ]; then continue; fi
    dya_zonmean_files+=( $mean_file )
    if [ -f $mean_file ]; then continue; fi

    cdo -P 4 -zonmean -timmean -selname,pr -cat $files $mean_file &
    if (( $(jobs -rp | wc -l) >= NUM_PROCS )); then
        wait -n   # wait for *one* job to finish (bash 5+)
    fi
done
mean_file=$OUTPUT_DIR/DYAMOND.nc
if [ ! -f $mean_file ]
then
    cdo -P 4 -ensmean -cat $dya_zonmean_files $mean_file
fi

# (February) Zonal means of IMERG data
files=$IMERG_FOLDER/20??/20??02*.nc
mean_file=$OUTPUT_DIR/IMERG.nc
if [ ! -f $mean_file ]
then
    cdo -P 4 zonmean -timmean -setname,pr -selname,precipitation -cat $files $mean_file &
fi

# Means of ERA5 data
files=$ERA5_RAW_FOLDER/*/*_02_era5_raw.nc
mean_file=$OUTPUT_DIR/ERA5.nc
if [ ! -f $mean_file ]
then
    cdo -P 4 -zonmean -timmean -mulc,1000 -setname,pr -selname,total_precipitation -cat $files $mean_file &
fi
wait
