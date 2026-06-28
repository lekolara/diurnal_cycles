# Diurnal Cycles of Deep Convective Processes in Satellite Measurements, the ERA5 Reanalysis and DYAMOND km-scale Models

This project contains scripts for downloading data from the DYAMOND project, ERA5 and IMERG (`scripts/remap_scripts/`), pre-processing, including combining the data into a common grid with conservative remapping from CDO (Climate Data Operators) (`scripts/remap_scripts/`) and computing data on a diurnal (`scripts/diurnal_cycles/`) and zonal level (`scripts/zonal_means/`). It also contains notebooks (`scripts/visualisation`) where the processed data is plotted. 

Note: The grid descriptors that are required for the remapping are also available on DYAMOND and scripts for that are available in this [repository](https://git.chalmers.se/see/geo/clouds-and-precipitation/papers/atmicemodelstatus/-/tree/main/code/DYAMOND_vs_CCIC/scripts/dkrz-levante). If you do not have access, it is the code used for [this paper](https://doi.org/10.5194/egusphere-2025-4634).

This work was a continuation of a master's thesis, so processing procedure can differ slightly between differen variables. There, the term used instead of FWP was TIWP, but they refer to the same variable. I made a graphic overview of the process in `Workflow.png`, which might help in navigation.

The pre-processing to a monthly diurnal dataset of CCIC, which was used in this paper is not present in this repository, can be found in The Chalmers Cloud Ice Climatology [repository](https://github.com/SEE-GEO/ccic/tree/0.1pre). Specifically, https://github.com/SEE-GEO/ccic/blob/main/scripts/monthly_means.py.
