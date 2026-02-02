# Remapping
This project contains some bash scripts download the DYAMOND precipitation data on disk (`scripts/download_dyamond.sh`). The downloaded data can then be combined into a common grid with conservative remapping from CDO (Climate Data Operators) (`scripts/remap_dyamond.sh`). Additionally, you can perform a conservative remapping of the IMERG data (`scripts/remap_IMERG.sh`). Finally, there is a simple bash-script to compute zonal means of ERA5, IMERG, and DYAMOND (`scripts/zonal_means.py`). These can be plotted (`plots/zonal_means.py`).

Note: The grid descriptors that are required for the remapping are also available on DYAMOND and scripts for that are available in this [repository](https://git.chalmers.se/see/geo/clouds-and-precipitation/papers/atmicemodelstatus/-/tree/main/code/DYAMOND_vs_CCIC/scripts/dkrz-levante). If you do not have access, it is the code used for [this paper](https://doi.org/10.5194/egusphere-2025-4634).

Note: The plot of the zonal means is currently incomplete/wrong because the MPAS and gSAM models from the DYAMOND winter run contain incorrect/unknown unit annotations.
