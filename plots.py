# %%
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib as mpl
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cmocean
import cmcrameri
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.patches import Rectangle

cmap_amp = cmcrameri.cm.devon
cmap_amp = cmocean.tools.crop_by_percent(cmap_amp, 20, which='min', N=None)

regions_plot = {
    "Africa": {"color": "#eaac8bff", "lon": [15, 35], "lat": [-20, 5]},
    "Tropical Indian": {"color": "#b56576ff", "lon": [55, 95], "lat": [-20, 0]},
    "Maritime Continent": {"color": "#e56b6fff", "lon": [95, 150], "lat": [-10, 10]},
    "North Pacific": {"color": "#355070ff", "lon": [140, 200], "lat": [15, 30]},
    "Tropical Pacific": {"color": "#6d597aff", "lon": [160, 200], "lat": [-20, 0]},
    "South America": {"color": "#e88c7dff", "lon": [285, 320], "lat": [-15, 0]},
}

mpl.rcParams.update({
        "text.usetex": True,
        "font.family": "serif",
        "text.latex.preamble": r"\usepackage{amsmath}"
    })
plt.rcParams.update({'font.size': 20, 'axes.titlesize': 24, 'axes.labelsize': 20, 'legend.fontsize': 14, 'xtick.labelsize': 20, 'ytick.labelsize': 20})


# Zonal means of seasonal precipitation

def plot_Seasonal_zonal_means(dataset1, dataset2):

    # Define seasons
    seasons = {
        "DJF": [12, 1, 2],
        "MAM": [3, 4, 5],
        "JJA": [6, 7, 8],
        "SON": [9, 10, 11]
    }

    # Get latitude coordinate name
    lat_name = "lat" if "lat" in dataset1.coords else "latitude"

    # Colorblind-friendly colors (matplotlib tab10)
    imerg_color = '#6D597A'
    era5_color = '#e56b6fff'
    colors = {
        "IMERG": imerg_color,
        "ERA5": era5_color
    }
    season_linestyles = ['-', '--', '-.', ':']
    season_names = ['DJF', 'MAM', 'JJA', 'SON']


    plt.figure(figsize=(10, 6))

    for dataset, label in zip([dataset1, dataset2], ["IMERG", "ERA5"]):
        for season, months in seasons.items():
            # Select months, handle December (12) for DJF
            months_sel = months
            # For DJF, need to handle December from previous year
            if season == "DJF":
                da = dataset["pr"].sel(month=months_sel)
                # If December is not present, skip
                if 12 not in dataset["month"]:
                    da = da.sel(month=[m for m in months_sel if m != 12])
            else:
                da = dataset["pr"].sel(month=months_sel)
            # Mean over months
            da_season = da.mean("month")
            plt.plot(dataset[lat_name], da_season, label=f"{label} {season}", color=colors[label], linestyle=season_linestyles[season_names.index(season)], linewidth=2)

    plt.xlabel("Latitude")
    plt.ylabel("Zonal Mean Precipitation (mm/hr)")
    #plt.title("Seasonal Zonal Mean Precipitation 2018-2023: IMERG vs ERA5")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    return plt

def zonal_means_february(data_path, model_files):

    # DYAMOND models (excluding ERA5 and IMERG)
    dyamond_models = [k for k in model_files if k not in ["ERA5", "IMERG"]]


    imerg_color = '#6D597A'
    era5_color = '#e56b6fff'
    dyamond_color = '#E88C7D'
    colors = [imerg_color, era5_color]
    linestyles = ['--','-',':']


    plt.figure(figsize=(10, 6))

    # Load DYAMOND model data and compute spread
    dyamond_lat = None
    dyamond_vals = []
    for label in dyamond_models:
        fname = model_files[label]
        fpath = os.path.join(data_path, fname)
        if not os.path.exists(fpath):
            print(f"File not found: {fpath}")
            continue
        ds = xr.open_dataset(fpath)
        var = None
        for v in ds.data_vars:
            if "pr" in v or "precipitation" in v or "total_precipitation" in v:
                var = v
                break
        if var is None:
            var = list(ds.data_vars)[0]
        lat_name = "lat" if "lat" in ds.coords else "latitude"
        if dyamond_lat is None:
            dyamond_lat = ds[lat_name].values
        dyamond_vals.append(ds[var].values)
    # Plot DYAMOND mean
    dyamond_mean = np.mean(dyamond_vals, axis=0)
    plt.plot(dyamond_lat, dyamond_mean, label='DYAMOND Mean', color=dyamond_color, linestyle=':', linewidth=2)
    # Plot DYAMOND spread as shaded area
    if dyamond_vals:
        dyamond_vals = np.stack(dyamond_vals)
        dyamond_min = np.min(dyamond_vals, axis=0)
        dyamond_max = np.max(dyamond_vals, axis=0)
        plt.fill_between(dyamond_lat, dyamond_min, dyamond_max, color='gray', alpha=0.4, label='DYAMOND spread')

    # Plot ERA5 and IMERG as lines
    for idx, label in enumerate(["IMERG", "ERA5"]):
        fname = model_files[label]
        fpath = os.path.join(data_path, fname)
        if not os.path.exists(fpath):
            print(f"File not found: {fpath}")
            continue
        ds = xr.open_dataset(fpath)
        var = None
        for v in ds.data_vars:
            if "pr" in v or "precipitation" in v or "total_precipitation" in v:
                var = v
                break
        if var is None:
            var = list(ds.data_vars)[0]
        lat_name = "lat" if "lat" in ds.coords else "latitude"
        plt.plot(ds[lat_name], ds[var], label=label, color=colors[idx], linestyle=linestyles[idx], linewidth=2)

    plt.xlabel("Latitude")
    plt.ylabel("Zonal Mean Precipitation (mm/hr)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    return plt

# %%
