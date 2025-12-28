# %%
import xarray as xr
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
# %%

fit = xr.open_dataset('/data/s5/users/lara/master_thesis/data/ccic/CCIC_diurnal_fit_metrics_y.nc').sel(month = 1)                                                                       
values = xr.open_dataset('/data/s5/users/lara/master_thesis/data/ccic/CCIC_TIWP_diurnal_climatology_2018_2023_utc.nc').sel(month = 1)            
# %%
amplitude = fit.diurnal_amplitude
phase = fit.diurnal_phase
fitted = fit.diurnal_fit_fitted_values                  
coeff = fit.diurnal_fit_coeff_of_determination
tiwp = values.tiwp
# %%
num_lats, num_lons, num_times = tiwp.shape
random_indices = np.random.choice(num_lats * num_lons, 50, replace=False)
lat_indices, lon_indices = np.unravel_index(random_indices, (num_lats, num_lons))

fig, axes = plt.subplots(5, 10, figsize=(40, 20), sharex=True, sharey=True)
axes = axes.flatten()

for i, (lat_idx, lon_idx) in enumerate(zip(lat_indices, lon_indices)):
    obs = tiwp[:,lat_idx, lon_idx]
    fit = fitted[:,lat_idx, lon_idx]
    r2 = coeff[lat_idx, lon_idx].item()
    ax = axes[i]
    ax.plot(obs, label='TIWP', color='tab:blue')
    ax.plot(fit, label='Fitted', color='tab:orange')
    ax.set_title(f'Lat: {tiwp.lat[lat_idx]:.2f}\nLon: {tiwp.lon[lon_idx]:.2f}\n$R^2$={r2:.2f}', fontsize=8)
    ax.tick_params(labelsize=6)
    if i == 0:
        ax.legend(fontsize=6)
for j in range(i+1, 50):
    fig.delaxes(axes[j])
plt.tight_layout()
plt.show()
plt.savefig('tiwp_fitted_random_samples.png', dpi=300)
# %%
tiwp
# %%
