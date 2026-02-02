#!/usr/bin/env bash

# This script is used to remap the precipitation model outputs (previously
# downloaded from levante) to a given grid. It also renames all variables
# names to 'pr' and changes all units to 'mm/h'. The unit conversion is
# currently broken for MPAS and GSAM because their unit annotations are
# unclear.
# WARNING: Scripts need cdo >= 2.5.3 (conda will not work)
#
# Author: Nils Müller
# E-Mail: nils.n.mueller@gmail.com

set -euo pipefail
source config.sh

# gSAM is not correct here, it shows cummulative value, fixed in gSAM_conversion.py
# IFS is not converted from m to mm here, it also  it shows cummulative value, fixed in IFS_conversion.py

MASS_FLUX_TO_MM_H=3610.659
MM_15MIN_TO_MM_H=4
M_H_TO_MM_H=1000
PER_MODEL_CONVERSION=(
$MM_15MIN_TO_MM_H # ARPEGE -> pr (mm) (15 min)
$MASS_FLUX_TO_MM_H # GEOS -> pr (kg m-2 s-1) (15 min)
$MM_15MIN_TO_MM_H # gSAM -> pracc (mm) (15 min)
$MASS_FLUX_TO_MM_H # ICON -> pr (kg m-2 s-1) (15 min)
1 # IFS -> pracc (m) (1 h)
$MM_15MIN_TO_MM_H # MPAS -> pr (mm) (15 min)
$MASS_FLUX_TO_MM_H # SHiELD -> pr (kg m-2 s-1) (15 min)
)
MODEL_VAR_NAMES=(
pr # ARPEGE
pr # GEOS
pracc # gSAM
pr # ICON
pracc # IFS
pr # MPAS
pr # SHiELD
)
MODEL_EXTRAS=(
" " # ARPEGE
" " # GEOS
" " # gSAM
" " # ICON
" " # IFS
-setgrid,$DYA_GRID_FOLDER/MPAS_grid.nc # MPAS (some grid problems)
" " # SHiELD
)

weights_folder=$DYA_WEIGHTS_FOLDER/$(basename -s .txt $TARGET_GRID)
data_folder=$DYA_DATA_FOLDER/$(basename -s .txt $TARGET_GRID)

mkdir -p $weights_folder
mkdir -p $data_folder

if [ ! -f $TARGET_GRID ]
then
    echo "Target-grid description not found '$TARGET_GRID' -> Fail"
    exit 1
fi

# Clean DYAMOND-MPAS time dimension
for file in $DYA_RAW_FOLDER/MPAS
do
    ncrename -O -v xtime,time -d xtime,time $file &
    if (( $(jobs -rp | wc -l) >= NUM_PROCS ))
    then
        wait -n   # wait for *one* job to finish
    fi
done
wait

# Generate weights for the remapping
for ((model_idx=0; model_idx<NUM_MODELS; model_idx++))
do
    model="${DYA_MODEL_NAMES[model_idx]}"
    grid_file="$DYA_GRID_FOLDER/${model}_grid.nc"
    weight_file="$weights_folder/${model}_weights.nc"

    if [ -f $weight_file ]; then continue; fi
    if [ ! -f $grid_file ]
    then
        echo "$model :: grid-file not found '$grid_file' -> Skipping"
        continue
    fi

    echo "Model :: $model"
    cdo -gencon,"$TARGET_GRID" $grid_file $weight_file &
    # If number of background jobs >= NUM_PROCS, wait for one to finish
    if (( $(jobs -rp | wc -l) >= NUM_PROCS ))
    then
        wait -n   # wait for *one* job to finish
    fi
done
wait
echo "Finished weight-generation for all models"

# Remapping and cleaning
for ((model_idx=0; model_idx<NUM_MODELS; model_idx++))
do
    model=${DYA_MODEL_NAMES[model_idx]}
    grid_file=$DYA_GRID_FOLDER/${model}_grid.nc
    weight_file=$weights_folder/${model}_weights.nc
    src_folder=$DYA_RAW_FOLDER/$model
    out_folder=$data_folder/$model
    var_name=${MODEL_VAR_NAMES[model_idx]}
    factor=${PER_MODEL_CONVERSION[model_idx]}
    extra=${MODEL_EXTRAS[model_idx]}

    printf "%(%F %T)T | $model\n"
    mkdir -p $out_folder
    for src_file in $src_folder/*.nc
    do
        date_range=${src_file: -32:8}
        out_file=$out_folder/${date_range}.nc

        if [ -f $out_file ]; then continue; fi

        printf "%(%F %T)T | $model :: $date_range | Processing\n"
        cdo -s \
            -mulc,$factor \
            -remap,$TARGET_GRID,$weight_file \
            $extra \
            -setattribute,pr@long_name="surface precipitation rate [mm/h]" \
            -setattribute,pr@standard_name="precipitation_flux" \
            -setunit,"mm h-1" \
            -setname,pr \
            -selname,$var_name \
            $src_file $out_file &
        if (( $(jobs -rp | wc -l) >= NUM_PROCS ))
        then
            wait -n   # wait for *one* job to finish
        fi
    done
done
