from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

BASE_FOLDER = Path("/scratch/nilsmu/DYAMOND_precipitation/")
ZONAL_MEAN_FOLDER = BASE_FOLDER / "zonal_means/latlon_grid_1deg"

if __name__ == "__main__":
    assert ZONAL_MEAN_FOLDER.exists()

    plt.style.use("plot_style.mplstyle")
    fig = plt.figure(figsize=(5, 4))
    for filepath in ZONAL_MEAN_FOLDER.glob("*.nc"):
        if filepath.stem.startswith("IMERG_"):
            continue
        ds = xr.open_dataset(filepath)
        lat = ds["lat"]
        var = np.asarray(ds["pr"]).squeeze()
        match filepath.stem:
            case "gSAM":
                var *= 1 / 3610.659
        plt.plot(lat, var, label=filepath.stem)
    plt.legend()
    plt.xlabel("Latitude (deg)")
    plt.ylabel("Precipitation (mm/h)")
    plt.ylim(0)

    plt.savefig("zonal_means.png", dpi=200, bbox_inches="tight")
    plt.close()
