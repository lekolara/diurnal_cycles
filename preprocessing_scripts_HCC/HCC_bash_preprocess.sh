#!/bin/bash
#SBATCH -t 1-12:00:00
#SBATCH --ntasks=4
#SBATCH -C NOGPU

data_dir="/path/to/ccic"

apptainer exec --bind $data_dir:/data \
    ${data_dir}/ccic_a48ab441.sif \
    python /data/scripts/lara/hcc.py \
        --input_dir /data/output/lara \
        --output_zarr "/data/output/hcc_2018_${SLURM_ARRAY_TASK_ID}.zarr" \
        --threshold 0.360 \
        --year 2018 \
        --month ${SLURM_ARRAY_TASK_ID}

apptainer exec --bind $data_dir:/data \
    ${data_dir}/ccic_a48ab441.sif \
    python /data/scripts/lara/hcc.py \
        --input_dir /data/output/lara \
        --output_zarr "/data/output/hcc_2018_${SLURM_ARRAY_TASK_ID}_0p50.zarr" \
        --threshold 0.5 \
        --year 2018 \
        --month ${SLURM_ARRAY_TASK_ID}

apptainer exec --bind $data_dir:/data \
    ${data_dir}/ccic_a48ab441.sif \
    python /data/scripts/lara/hcc.py \
        --input_dir /data/output/lara \
        --output_zarr "/data/output/hcc_2018_${SLURM_ARRAY_TASK_ID}_0p75.zarr" \
        --threshold 0.75 \
        --year 2018 \
        --month ${SLURM_ARRAY_TASK_ID}

apptainer exec --bind $data_dir:/data \
    ${data_dir}/ccic_a48ab441.sif \
    python /data/scripts/lara/hcc.py \
        --input_dir /data/output/lara \
        --output_zarr "/data/output/hcc_2018_${SLURM_ARRAY_TASK_ID}_0p90.zarr" \
        --threshold 0.9 \
        --year 2018 \
        --month ${SLURM_ARRAY_TASK_ID}