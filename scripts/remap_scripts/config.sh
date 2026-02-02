#!/usr/bin/env bash
# Configuration of paths and such for the preparation of DYAMOND and IMERG data
#
# Author: Nils Müller
# E-Mail: nils.n.mueller@gmail.com

NUM_PROCS=32
TARGET_GRID=/scratch/leko/latlon_grid_1deg.txt

# LEVANTE (DKRZ) paths
LEVANTE_HOST_NAME=levante
LEVANTE_BASE_FOLDER=/fastdata/ka1081/DYAMOND/data/winter_data
LEVANTE_DATA_FOLDERS=(
# $LEVANTE_BASE_FOLDER/CMC/GEM/DW-ATM/atmos/1hr/pracc/r1i1p1f1/2d/gn (BROKEN)
$LEVANTE_BASE_FOLDER/METEOFR/ARPEGE-NH-2km/DW-ATM/atmos/15min/pr/r1i1p1f1/2d/gn
$LEVANTE_BASE_FOLDER/NASA/GEOS-3km/DW-ATM/atmos/15min/pr/r1i1p1f1/2d/gn
$LEVANTE_BASE_FOLDER/SBU/gSAM-4km/DW-ATM/atmos/15min/pracc/r1i1p1f1/2d/gn
$LEVANTE_BASE_FOLDER/MPIM-DWD-DKRZ/ICON-SAP-5km/DW-ATM/atmos/15min/pr/dpp0014/2d/gn
$LEVANTE_BASE_FOLDER/ECMWF/IFS-4km/DW-CPL/atmos/1hr/pracc/r1i1p1f1/2d/gn
$LEVANTE_BASE_FOLDER/NCAR/MPAS-3km/DW-ATM/atmos/15min/pr/r1i1p1f1/2d/gn
$LEVANTE_BASE_FOLDER/NOAA/SHiELD-3km/DW-ATM/atmos/15min/pr/r1i1p1f1/pl/gn
)

# ERA5 folders
ERA5_BASE_FOLDER=/scratch/leko/ERA5
ERA5_RAW_FOLDER=$ERA5_BASE_FOLDER/ERA5_raw

# IMERG folders
IMERG_BASE_FOLDER=/scratch/leko/IMERG
IMERG_RAW_FOLDERS=(
$IMERG_BASE_FOLDER/raw_data/GPM_IMERG_converted/GPM_3IMERGHH_2022_conv
$IMERG_BASE_FOLDER/raw_data/GPM_IMERG_converted/GPM_3IMERGHH_2023_conv
$IMERG_BASE_FOLDER/raw_data/G_Behrens_GPM_IMERG_raw/G_Behrens_GPM_IMERG_raw_2018
$IMERG_BASE_FOLDER/raw_data/G_Behrens_GPM_IMERG_raw/G_Behrens_GPM_IMERG_raw_2019
$IMERG_BASE_FOLDER/raw_data/G_Behrens_GPM_IMERG_raw/G_Behrens_GPM_IMERG_raw_2020
$IMERG_BASE_FOLDER/raw_data/G_Behrens_GPM_IMERG_raw/G_Behrens_GPM_IMERG_raw_2021
)
IMERG_DATA_FOLDER=$IMERG_BASE_FOLDER/data

# DYAMOND folders
DYA_BASE_FOLDER=/scratch/nilsmu/DYAMOND_precipitation
DYA_RAW_FOLDER=$DYA_BASE_FOLDER/raw
DYA_GRID_FOLDER=$DYA_BASE_FOLDER/grids
DYA_WEIGHTS_FOLDER=$DYA_BASE_FOLDER/weights
DYA_DATA_FOLDER=$DYA_BASE_FOLDER/data

DYA_MODEL_NAMES=(
ARPEGE
GEOS
gSAM
ICON
IFS
MPAS
SHiELD
)
NUM_MODELS=${#DYA_MODEL_NAMES[@]}
