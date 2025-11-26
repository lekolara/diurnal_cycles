#!/usr/bin/env bash

# This script is used to download the 2D model outputs from the levante supercomputer at the DKRZ in Hamburg.
# Note that the data could be moved to tape. In that case, you have to request the data (by e-mailing someone)
# Incomplete (and sometimes incorrect) information on the model data is located here:
# https://easy.gems.dkrz.de/DYAMOND/Winter/index.html
# https://easy.gems.dkrz.de/_static/DYAMOND/WINTER/variable_table.html
#
# Author: Nils Müller
# E-Mail: nils.n.mueller@gmail.com

set -euo pipefail
source config.sh

mkdir -p "$DYA_RAW_FOLDER"

DRYRUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRYRUN=true
    echo "Running in DRY-RUN mode (no files will be downloaded)."
fi

download_one() {
    remote_dir="$1"
    model="$2"

    local_dir=$DYA_RAW_FOLDER/$model
    mkdir -p $local_dir

    echo "Preparing ${model}:"
    echo "  Remote: $remote_dir"
    echo "  Local:  $local_dir"

    if $DRYRUN; then return; fi

    rsync --info=progress2 -a --partial --append-verify \
        --include="*gn_20200[2-3]*.nc" --exclude="*" \
        ${LEVANTE_HOST_NAME}:${remote_dir}/ $local_dir/ &
}

echo "Launching downloads..."
for ((model_idx=0; model_idx<NUM_MODELS; model_idx++))
do
    download_one "${LEVANTE_DATA_FOLDERS[model_idx]}" "${DYA_MODEL_NAMES[model_idx]}"
done

if ! $DRYRUN; then
    echo "Waiting for all downloads to finish..."
    wait
    echo "All downloads completed."
else
    echo "Dry run completed. No downloads were performed."
fi
