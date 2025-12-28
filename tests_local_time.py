# %%
import xarray as xr
import numpy as np

# %%

######################################################
#### Testing shift_diurnal_to_local_time function ####
######################################################


def shift_diurnal_to_local_time(da, hour_dim="hour_of_day", lon_dim="longitude"):
    """
    Shift diurnal cycle data from UTC to local solar time based on longitude.
    Supports both hourly (24 steps) and half-hourly (48 steps) data.
    Works for DataArray with shape (month, hour_of_day, lat, lon).
    Returns a DataArray with a new coordinate 'hour_of_day' (local time).
    """
    nsteps = da[hour_dim].size
    deg_per_step = 360 / nsteps
    # e.g. (360 degrees / 24 hours = 15 degrees per hour)
    lons = da[lon_dim].values
    shifted = da.copy(deep=True)
    # full, independent copy of the data is made, not just a reference to the original data.

    for i, lon in enumerate(lons):
        shift = int(np.round(lon / deg_per_step))
        shifted.loc[{lon_dim: lon}] = da.roll({hour_dim: shift}, roll_coords=False).loc[{lon_dim: lon}]
        # assigns the shifted data for this longitude back into the corresponding longitude slice of the shifted DataArray.
    return shifted


def shift_phase_to_lst(phase_da, lon_da):
    """Shift phase from UTC to local solar time using longitude array.
    Args:
        phase_da (xr.DataArray): phase in UTC, dims (..., lat, lon)
        lon_da (xr.DataArray): longitude array, dims (lon,) or (..., lon)
    Returns:
        xr.DataArray: phase in local solar time (LST)
    """
    # Broadcast lon to match phase_da dimensions
    lon2d = xr.broadcast(phase_da, lon_da)[1]

    phase_lst = phase_da + (lon2d / 360.0) * 24
    phase_lst = phase_lst.where(phase_lst <= 24, phase_lst - 24)
    return phase_lst


# %%

# --- Half-hourly longitude shift test ---
# This block creates a DataArray with half-hourly steps (0, 0.5, ..., 23.5)
# and every 7.5° longitude corresponds to a half-hour shift.
months_hh = [1]
hours_hh = np.arange(0, 24, 0.5)  # 48 half-hourly steps
lats_hh = np.array([0])
lons_hh = [0,7.5, -15, 22.5]  # 0, 7.5, ..., 352.5

# da_hh[hour=0, lon=0]=0, da_hh[hour=0, lon=7.5]=0.5, da_hh[hour=0, lon=15]=1, etc.
values_hh = np.zeros((1, len(hours_hh), 1, len(lons_hh)), dtype=float)
for i, lon in enumerate(lons_hh):
    for h, hour in enumerate(hours_hh):
        local_hour = (hour + lon / 15) % 24
        values_hh[0, h, 0, i] = local_hour

da_hh = xr.DataArray(
    values_hh,
    dims=("month", "hour_of_day", "lat", "longitude"),
    coords={
        "month": months_hh,
        "hour_of_day": hours_hh,
        "lat": lats_hh,
        "longitude": lons_hh,
    },
    name="pr"
)

print("\nHalf-hourly test DataArray (first hour at each longitude):")
for i, lon in enumerate(lons_hh):
    print(f"Longitude {lon}°: {da_hh.isel(month=0, hour_of_day=0, lat=0, longitude=i).values}")

# %%

#Hourly data test
# Dimensions
months = [1]
hours = np.arange(0,24)                         # 24 hourly steps
lats = np.array([0])                          # 1 latitude
lons = np.array([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])             # easy longitude offsets

# Create values so that da[hour=0, lon=lon] = (0 + lon//15) % 24
values = np.zeros((1, 24, 1, len(lons)), dtype=int)
for i, lon in enumerate(lons):
    for h in range(len(hours)):
        local_hour = (h + lon // 15) % 24
        values[0, h, 0, i] = local_hour

da = xr.DataArray(
    values,
    dims=("month", "hour_of_day", "lat", "longitude"),
    coords={
        "month": months,
        "hour_of_day": hours,
        "lat": lats,
        "longitude": lons,
    },
    name="pr"
)

print("ORIGINAL DATA")
for lon in lons:
    print(f"\nLongitude {lon}°:")
    print(da.sel(longitude=lon).isel(month=0, lat=0).values)

# %%

shifted = shift_diurnal_to_local_time(da, hour_dim="hour_of_day", lon_dim="longitude")

print("\n\nSHIFTED DATA (LOCAL TIME)")
for lon in lons:
    print(f"\nLongitude {lon}°:")
    print(shifted.sel(longitude=lon).isel(month=0, lat=0).values)
# %%

# %%
#Hourly data test
# Dimensions
months = [1]
hours = np.arange(0,24)                         # 24 hourly steps
lats = np.array([0])                          # 1 latitude
lons = np.arange(15.5,35.5)  # easy longitude offsets

# Stack hours at every longitude
values = hours.reshape((1, len(hours), 1, 1)) * np.ones((1, 1, 1, len(lons)), dtype=int)


da = xr.DataArray(
    values,
    dims=("month", "hour_of_day", "lat", "longitude"),
    coords={
        "month": months,
        "hour_of_day": hours,
        "lat": lats,
        "longitude": lons,
    },
    name="pr"
)

print("ORIGINAL DATA")
for lon in lons:
    print(f"\nLongitude {lon}°:")
    print(da.sel(longitude=lon).isel(month=0, lat=0).values)
# %%

shifted = shift_phase_to_lst(da, lon_da=da.longitude)

print("\n\nSHIFTED DATA (LOCAL TIME)")
for lon in lons:
    print(f"\nLongitude {lon}°:")
    print(shifted.sel(longitude=lon).isel(month=0, lat=0).values)
# %%
# sel longitude from 0 to 15
shifted.isel(hour_of_day = 0).isel(month=0, lat=0).mean()
# %%
shifted
# %%
