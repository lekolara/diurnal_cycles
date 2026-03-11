# Remapping
This project contains scripts for downloading data from the DYAMOND project, ERA5 and IMERG (`scripts/remap_scripts/`), pre-processing, including combining the data into a common grid with conservative remapping from CDO (Climate Data Operators) (`scripts/remap_scripts/`) and computing data on a diurnal (`scripts/diurnal_cycles/`) and zonal level (`scripts/zonal_means/`). It also contains notebooks where the processed data is plotted. A graphic overview of different scripts and notebooks and what they do is visible in `Workflow and scripts.png`.

Note: The grid descriptors that are required for the remapping are also available on DYAMOND and scripts for that are available in this [repository](https://git.chalmers.se/see/geo/clouds-and-precipitation/papers/atmicemodelstatus/-/tree/main/code/DYAMOND_vs_CCIC/scripts/dkrz-levante). If you do not have access, it is the code used for [this paper](https://doi.org/10.5194/egusphere-2025-4634).

