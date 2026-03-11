#!/usr/bin/env python3
##############################################################################################################
# Script to fit a harmonic function to the diurnal cycle of TIWP and calculate the amplitude 
# fit and coefficient of determination (R^2) for each grid point and month. 


import xarray as xr
import numpy as np
from pathlib import Path
from scipy.linalg import lstsq
from scipy.stats import pearsonr
import os


def sinfit2d_with_metrics(x, y):

    '''
    Fit a 24-hour and 12-hour sinusoidal cycle to the data and calculate metrics.   
    Parameters
    x : numpy array, The x-axis data (time)                         
    y : xarray Dataarray, The y-axis data (TIWP)    

    Returns
    y_fit : xarray DataArray, The fitted values of the harmonic fit
    coeff_of_determination_map : xarray DataArray, The coefficient of determination (R^2) for each grid point

    Coefficient of determination (R^2) is a measure of how well the model explains the variance in the data.
    It is defined as 1 minus the ratio of the residual sum of squares to the total sum of squares.


    '''
    A = np.ones(len(x))
    ls = [24, 12] # periods to fit
    for period in ls:
        A = np.column_stack((
            A,
            np.sin(2 * np.pi * x / period),
            np.cos(2 * np.pi * x / period)
        ))
    
    # Prepare output arrays
    b = np.full((A.shape[1], y.shape[1], y.shape[2]), np.nan)
    coeff_of_determination_map = np.full((y.shape[1], y.shape[2]), np.nan)
    #coeff_of_determination_24_map = np.full((y.shape[1], y.shape[2]), np.nan)
    #coeff_of_determination_12_map = np.full((y.shape[1], y.shape[2]), np.nan)

    for i in range(y.shape[1]):
        for j in range(y.shape[2]):
            y_ij = y[:, i, j]
            if not np.isnan(y_ij).any():
                b[:, i, j], _, _, _ = lstsq(A, y_ij)
                
                
    # Save coefficients
    m0 = b[0]
    s1 = b[1]
    c1 = b[2]
    s2 = b[3]
    c2 = b[4]

    y_fit = np.zeros((24, s1.shape[0], s1.shape[1]))  # (time, lat, lon)
    for i in range(s1.shape[0]):  
        for j in range(s1.shape[1]): 
            y_ij = y[:, i, j]
            # full fit
            y_fit[:, i, j] = (s1[i,j] * np.sin(2 * np.pi * x / 24) +
                            c1[i,j] * np.cos(2 * np.pi * x / 24) +
                            s2[i,j] * np.sin(2 * np.pi * x / 12) +
                            c2[i,j] * np.cos(2 * np.pi * x / 12)+
                            m0[i,j])
            
            # 24-hour component
            # y_fit_24 = s1[i,j] * np.sin(2 * np.pi * x / 24) + c1[i,j] * np.cos(2 * np.pi * x / 24) + m0[i,j]
            # 12-hour component
            #y_fit_12 = s2[i,j] * np.sin(2 * np.pi * x / 12) + c2[i,j] * np.cos(2 * np.pi * x / 12) + m0[i,j]
            
            # Compute R (Pearson correlation)
            #R_map[i, j], _ = pearsonr(y_ij, y_fit[:,i,j])
            
            # Compute total sum of squares and residual sum of squares
            ss_res = np.sum((y_ij - y_fit[:,i,j])**2)
            ss_tot = np.sum((y_ij - np.mean(y_ij))**2)
            # Compute coefficient of determination (R^2)
            coeff_of_determination_map[i, j] = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
            # Compute coefficient of determination (R^2) for 24-hour and 12-hour components
            # ss_res_24 = np.sum((y_ij - y_fit_24)**2)
            # ss_res_12 = np.sum((y_ij - y_fit_12)**2)
            #coeff_of_determination_24_map[i, j] = 1 - (ss_res_24 / ss_tot) if ss_tot > 0 else np.nan
            #coeff_of_determination_12_map[i, j] = 1 - (ss_res_12 / ss_tot) if ss_tot > 0 else np.nan
    

    # Convert to xarray DataArrays
    y_fit = xr.DataArray(y_fit, dims=["hour_of_day", "lat", "lon"], coords={"hour_of_day": x, "lat": y.lat, "lon": y.lon})
    coeff_of_determination_map = xr.DataArray(coeff_of_determination_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    #coeff_of_determination_24_map = xr.DataArray(coeff_of_determination_24_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    #coeff_of_determination_12_map = xr.DataArray(coeff_of_determination_12_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})

    return y_fit, coeff_of_determination_map


def fitted_amplitude(y_fit, relative = None):  

    A_total_ptp = y_fit.max(dim='hour_of_day') - y_fit.min(dim='hour_of_day')  # Peak-to-peak amplitude

    if relative:
        mean = y_fit.mean(dim = 'hour_of_day').values
        A_total_ptp = A_total_ptp/mean
    
    
    return A_total_ptp


# --------------------------------------------------
# USER SETTINGS
# --------------------------------------------------
# CCIC
# INPUT_FILES = ["/data/s5/users/lara/master_thesis/data/ccic/CCIC_TIWP_diurnal_climatology_2018_2023_utc.nc"]

# VAR_NAME = "tiwp"          # tiwp variable
# RELATIVE = False        # True -> normalize by monthly mean


# if RELATIVE:
#     OUTPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_fit_utc_relative_new.nc" for _ in INPUT_FILES]
# else:
#     OUTPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_fit_utc_new.nc" for _ in INPUT_FILES]


# ERA5
# INPUT_FILES = ["/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_climatology_2018_2023_utc.nc"]

# VAR_NAME = "tiwp"          # tiwp variable
# RELATIVE = False        # True -> normalize by monthly mean


# if RELATIVE:
#     OUTPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_fit_utc_relative_new.nc" for _ in INPUT_FILES]
# else:
#     OUTPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_fit_utc_new.nc" for _ in INPUT_FILES]

# DYAMOND MODELS
MODELS = ["ARPEGE", "GEOS", "GSAM", "ICON", "IFS", "MPAS", "GEM", "GFDL", "GRIST"]
INPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/DYAMOND/{model}_diurnal_feb2020_utc.nc" for model in MODELS]
VAR_NAME = "tiwp"          # tiwp variable
RELATIVE = False        # True -> normalize by monthly mean             
OUTPUT_FILES = [f"/data/s5/users/lara/master_thesis/data/DYAMOND/{model}_diurnal_fit_feb2020_utc.nc" for model in MODELS]

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

for INPUT_FILE, OUTPUT_FILE in zip(INPUT_FILES, OUTPUT_FILES):              
    print("Opening file...")
    ds = xr.open_dataset(INPUT_FILE)
    da = ds[VAR_NAME]   # DataArray (month, hour_of_day, lon, lat)
    da = da.where(da > 0)  # Mask negative values

    # Reorder dims for your fitter:
    # (time, lat, lon)
    if 'month' not in da.dims:
        da = da.expand_dims('month')
    da = da.transpose('month', 'hour_of_day', 'lat', 'lon')

    x = np.arange(24)

    monthly_amplitudes = []
    monthly_coefficient_of_determination = []
    monthly_fitted_values = []

    # --------------------------------------------------
    # MONTHLY LOOP
    # --------------------------------------------------

    print("Computing monthly amplitudes...")

    months = da.month

    for m in months.values:
        print(f"  Month {m}")

        # Select single month
        y = da.sel(month=m)    # (hour_of_day, lat, lon)

        # --- Harmonic fit ---
        y_fit, coeff_of_determination_map = sinfit2d_with_metrics(x, y)

        # --- Amplitudes ---
        A_total = fitted_amplitude(
            y_fit, relative=RELATIVE
        )

        # Store *total* diurnal amplitude
        monthly_amplitudes.append(A_total)
        monthly_coefficient_of_determination.append(coeff_of_determination_map)
        monthly_fitted_values.append(y_fit)
    # --------------------------------------------------
    # BUILD OUTPUT DATASET
    # --------------------------------------------------

    amp_month = xr.concat(monthly_amplitudes, dim="month")
    amp_month = amp_month.assign_coords(month=months)

    amp_month.name = "diurnal_amplitude"

    amp_month.attrs = {
        "long_name": "Peak-to-peak diurnal tiwp amplitude",
        "units": "kg/m^2" if not RELATIVE else "fraction of mean",
        "description": "24h+12h harmonic fit peak-to-peak amplitude",
        "source_file": INPUT_FILE,
    }


    coeff_of_determination_month = xr.concat(monthly_coefficient_of_determination, dim="month")
    coeff_of_determination_month = coeff_of_determination_month.assign_coords(month=months)
    coeff_of_determination_month.name = "coefficient_of_determination"
    coeff_of_determination_month.attrs = {
        "long_name": "Coefficient of determination (R^2) of diurnal tiwp fit",
        "units": "1",
        "description": "Coefficient of determination (R^2) for 24h+12h harmonic fit",
        "source_file": INPUT_FILE,
    }


    fitted_values_month = xr.concat(monthly_fitted_values, dim="month")
    fitted_values_month = fitted_values_month.assign_coords(month=months)
    fitted_values_month.name = "diurnal_fit_values"
    fitted_values_month.attrs = {
        "long_name": "Fitted values of diurnal tiwp fit",
        "units": "kg/m^2" if not RELATIVE else "fraction of mean",
        "description": "Fitted values for 24h+12h harmonic fit",
        "source_file": INPUT_FILE,
    }

    # BUILD FINAL DATASET

    ds_out = xr.Dataset({
        "diurnal_amplitude": amp_month,
        "diurnal_fit_coeff_of_determination": coeff_of_determination_month,
        "diurnal_fit_values": fitted_values_month
    })


    # --------------------------------------------------
    # SAVE TO NETCDF
    # --------------------------------------------------
    # If output file exists, remove it

    for file in [OUTPUT_FILE]:
        if os.path.exists(file):
            print(f"Removing existing file: {file}")
            os.remove(file)

    print("Saving output file...")
    # amp_month.to_netcdf(OUTPUT_FILE_AMPLITUDE)
    # phase_month.to_netcdf(OUTPUT_FILE_PHASE)
    ds_out.to_netcdf(OUTPUT_FILE)

    print("Done!")
    # print("Output written to:", OUTPUT_FILE_AMPLITUDE)
    # print("Output written to:", OUTPUT_FILE_PHASE)
    print("Output written to:", OUTPUT_FILE)