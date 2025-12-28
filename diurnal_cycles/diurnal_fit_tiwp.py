#!/usr/bin/env python3

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
    s1 : xarray Dataarray, Sine amplitude for 24-hour component
    c1 : xarray Dataarray, Cosine amplitude for 24-hour component
    s2 : xarray Dataarray, Sine amplitude for 12-hour component
    c2 : xarray Dataarray, Cosine amplitude for 12-hour component
    coeff_of_determination_map : xarray Dataarray, Coefficient of determination (R^2) for the full fit
    coeff_of_determination_24_map : xarray Dataarray, Coefficient of determination (R^2) for the 24-hour component
    coeff_of_determination_12_map : xarray Dataarray, Coefficient of determination (R^2) for the 12-hour component
    residuals_map : xarray Dataarray, Residuals of the fit
    R_map : xarray Dataarray, Pearson correlation coefficient of the fit

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
    A = A[:, 1:]  # remove constant column


    # Allocate arrays
    b = np.full((A.shape[1], y.shape[1], y.shape[2]), np.nan)
    R_map = np.full((y.shape[1], y.shape[2]), np.nan)
    residuals_map = np.full((y.shape[1], y.shape[2]), np.nan)
    coeff_of_determination_map = np.full((y.shape[1], y.shape[2]), np.nan)
    #coeff_of_determination_24_map = np.full((y.shape[1], y.shape[2]), np.nan)
    #coeff_of_determination_12_map = np.full((y.shape[1], y.shape[2]), np.nan)

    for i in range(y.shape[1]):
        for j in range(y.shape[2]):
            y_ij = y[:, i, j]
            if not np.isnan(y_ij).any():
                b[:, i, j], residuals_map[i, j], _, _ = lstsq(A, y_ij)
                
                
    # Save coefficients
    m0 = y.mean(dim = 'hour_of_day').values
    s1 = b[0]
    c1 = b[1]
    s2 = b[2]
    c2 = b[3]

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
            y_fit_24 = s1[i,j] * np.sin(2 * np.pi * x / 24) + c1[i,j] * np.cos(2 * np.pi * x / 24) + m0[i,j]
            # 12-hour component
            y_fit_12 = s2[i,j] * np.sin(2 * np.pi * x / 12) + c2[i,j] * np.cos(2 * np.pi * x / 12) + m0[i,j]
            
            # Compute R (Pearson correlation)
            #R_map[i, j], _ = pearsonr(y_ij, y_fit[:,i,j])
            
            # Compute total sum of squares and residual sum of squares
            ss_res = np.sum((y_ij - y_fit[:,i,j])**2)
            ss_tot = np.sum((y_ij - np.mean(y_ij))**2)
            # Compute coefficient of determination (R^2)
            coeff_of_determination_map[i, j] = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
            # Compute coefficient of determination (R^2) for 24-hour and 12-hour components
            ss_res_24 = np.sum((y_ij - y_fit_24)**2)
            ss_res_12 = np.sum((y_ij - y_fit_12)**2)
            #coeff_of_determination_24_map[i, j] = 1 - (ss_res_24 / ss_tot) if ss_tot > 0 else np.nan
            #coeff_of_determination_12_map[i, j] = 1 - (ss_res_12 / ss_tot) if ss_tot > 0 else np.nan
    

    # Convert to xarray DataArrays
    s1 = xr.DataArray(s1, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    c1 = xr.DataArray(c1, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    s2 = xr.DataArray(s2, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    c2 = xr.DataArray(c2, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    R_map = xr.DataArray(R_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    residuals_map = xr.DataArray(residuals_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    coeff_of_determination_map = xr.DataArray(coeff_of_determination_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    #coeff_of_determination_24_map = xr.DataArray(coeff_of_determination_24_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})
    #coeff_of_determination_12_map = xr.DataArray(coeff_of_determination_12_map, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})

    return s1, c1, s2, c2, coeff_of_determination_map, residuals_map


def fitted_amplitude_phase(s1, c1, s2, c2, y, relative = None):

    """
    Calculate the amplitude of the fitted diurnal cycle.

    Parameters
    s1 : xarray Dataarray, Sine amplitude for 24-hour component
    c1 : xarray Dataarray, Cosine amplitude for 24-hour component
    s2 : xarray Dataarray, Sine amplitude for 12-hour component
    c2 : xarray Dataarray, Cosine amplitude for 12-hour component
    x : numpy array, The x-axis data (time)
    y : xarray Dataarray, The y-axis data (TIWP)                                                            

    Returns     
    A1 : xarray Dataarray, 24-hour amplitude
    A2 : xarray Dataarray, 12-hour amplitude
    A_total_xr : xarray Dataarray, Peak-to-peak amplitude

    """                             

    # Convert to numpy array
    s1 = s1.values
    c1 = c1.values
    s2 = s2.values
    c2 = c2.values

    
    # Compute diurnal cycle for each lat/lon point
    x = np.arange(0, 24, 1)
    y_fit = np.zeros((24, s1.shape[0], s1.shape[1]))  # (time, lat, lon)
    for i in range(s1.shape[0]):  
        for j in range(s1.shape[1]): 
            y_fit[:, i, j] = (s1[i,j] * np.sin(2 * np.pi * x / 24) +
                            c1[i,j] * np.cos(2 * np.pi * x / 24) +
                            s2[i,j] * np.sin(2 * np.pi * x / 12) +
                            c2[i,j] * np.cos(2 * np.pi * x / 12))
            
    y_fit = y_fit + y.mean(dim = 'hour_of_day').values  # Add mean back to fit

    A_total_ptp = y_fit.max(axis = 0) - y_fit.min(axis = 0)  # Peak-to-peak amplitude

    if relative:
        mean = y.mean(dim = 'hour_of_day').values
        A_total_ptp = A_total_ptp/mean
    
    # Convert to xarray
    A_total_ptp = xr.DataArray(A_total_ptp, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})

    # Find peak time
    t_peak = y_fit.argmax(axis = 0)

    # Convert to xarray
    t_peak_xr = xr.DataArray(t_peak, dims=["lat", "lon"], coords={"lat": y.lat, "lon": y.lon})

    y_fit = xr.DataArray(y_fit, dims=["hour_of_day", "lat", "lon"], coords={"hour_of_day": x, "lat": y.lat, "lon": y.lon})
    
    return A_total_ptp, t_peak_xr, y_fit


# --------------------------------------------------
# USER SETTINGS
# --------------------------------------------------
# CCIC
# INPUT_FILE = "/data/s5/users/lara/master_thesis/data/ccic/CCIC_TIWP_diurnal_climatology_2018_2023_utc.nc"

# VAR_NAME = "tiwp"          # tiwp variable
# RELATIVE = False        # True -> normalize by monthly mean


# if RELATIVE:
#     OUTPUT_FILE_AMPLITUDE = f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_amplitude_relative.nc"
# else:
#     OUTPUT_FILE_AMPLITUDE = f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_amplitude.nc"

# OUTPUT_FILE_PHASE = f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_phase_utc.nc"

# OUTPUT_FILE_FIT = f"/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_fit_metrics_y.nc"
# ERA5
INPUT_FILE = "/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_climatology_2018_2023_utc.nc"

VAR_NAME = "tiwp"          # tiwp variable
RELATIVE = False        # True -> normalize by monthly mean


if RELATIVE:
    OUTPUT_FILE_AMPLITUDE = f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_amplitude_relative.nc"
else:
    OUTPUT_FILE_AMPLITUDE = f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_amplitude.nc"

OUTPUT_FILE_PHASE = f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_phase_utc.nc"

OUTPUT_FILE_FIT = f"/data/s5/users/lara/master_thesis/data/ERA5/ERA5_diurnal_fit_metrics_y.nc"

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

print("Opening file...")
ds = xr.open_dataset(INPUT_FILE)
da = ds[VAR_NAME]   # DataArray (month, hour_of_day, lon, lat)
da = da.where(da > 0)  # Mask negative values

# Reorder dims for your fitter:
# (time, lat, lon)
da = da.transpose("month", "hour_of_day", "lat", "lon")

x = np.arange(24)

monthly_amplitudes = []
monthly_peaks = []
monthly_coefficient_of_determination = []
monthly_residuals = []
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
    s1, c1, s2, c2, coeff_of_determination_map, residuals_map = sinfit2d_with_metrics(x, y)

    # --- Amplitudes ---
    A_total, t_peak, y_fit = fitted_amplitude_phase(
        s1, c1, s2, c2, y, relative=RELATIVE
    )

    # Store *total* diurnal amplitude
    monthly_amplitudes.append(A_total)
    monthly_peaks.append(t_peak)
    monthly_coefficient_of_determination.append(coeff_of_determination_map)
    monthly_residuals.append(residuals_map)
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

phase_month = xr.concat(monthly_peaks, dim="month")
phase_month = phase_month.assign_coords(month=months)

phase_month.name = "diurnal_phase"

phase_month.attrs = {
    "long_name": "Peak diurnal tiwp time",
    "units": "hour of day",
    "description": "24h+12h harmonic fit peak time",
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

residuals_month = xr.concat(monthly_residuals, dim="month")
residuals_month = residuals_month.assign_coords(month=months)
residuals_month.name = "residuals"
residuals_month.attrs = {
    "long_name": "Residuals of diurnal tiwp fit",
    "units": "kg/m^2",
    "description": "Residuals for 24h+12h harmonic fit",
    "source_file": INPUT_FILE,
}

fitted_values_month = xr.concat(monthly_fitted_values, dim="month")
fitted_values_month = fitted_values_month.assign_coords(month=months)
fitted_values_month.name = "fitted_values"
fitted_values_month.attrs = {
    "long_name": "Fitted values of diurnal tiwp fit",
    "units": "kg/m^2" if not RELATIVE else "fraction of mean",
    "description": "Fitted values for 24h+12h harmonic fit",
    "source_file": INPUT_FILE,
}

# BUILD FINAL DATASET

ds_out = xr.Dataset({
    "diurnal_amplitude": amp_month,
    "diurnal_phase": phase_month,
    "diurnal_fit_coeff_of_determination": coeff_of_determination_month,
    "diurnal_fit_residuals": residuals_month,
    "diurnal_fit_fitted_values": fitted_values_month
})


# --------------------------------------------------
# SAVE TO NETCDF
# --------------------------------------------------
# If output file exists, remove it

# for file in [OUTPUT_FILE_AMPLITUDE, OUTPUT_FILE_PHASE]:
#     if os.path.exists(file):
#         print(f"Removing existing file: {file}")
#         os.remove(file)

for file in [OUTPUT_FILE_FIT]:
    if os.path.exists(file):
        print(f"Removing existing file: {file}")
        os.remove(file)

print("Saving output file...")
# amp_month.to_netcdf(OUTPUT_FILE_AMPLITUDE)
# phase_month.to_netcdf(OUTPUT_FILE_PHASE)
ds_out.to_netcdf(OUTPUT_FILE_FIT)

print("Done!")
# print("Output written to:", OUTPUT_FILE_AMPLITUDE)
# print("Output written to:", OUTPUT_FILE_PHASE)
print("Output written to:", OUTPUT_FILE_FIT)