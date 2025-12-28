# %%
import numpy as np
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap
from colorspacious import cspace_convert

def soften_twilight_cam02(
    Lmin=45,
    Lmax=75,
    N=256,
    base_cmap="twilight_shifted"
):
    cmap = cm.get_cmap(base_cmap, N)
    rgb = cmap(np.linspace(0, 1, N))[:, :3]

    # RGB → CAM02-UCS
    cam = cspace_convert(rgb, "sRGB1", "CAM02-UCS")

    # cam[:, 0] is J' (perceptual lightness)
    J = cam[:, 0]
    cam[:, 0] = np.interp(J, (J.min(), J.max()), (Lmin, Lmax))

    # Back to RGB
    rgb_new = cspace_convert(cam, "CAM02-UCS", "sRGB1")

    # Clip just in case of minor gamut excursions
    rgb_new = np.clip(rgb_new, 0, 1)

    return LinearSegmentedColormap.from_list(
        "twilight_soft",
        rgb_new
    )

soft_twilight = soften_twilight_cam02()
# %%
soft_twilight
# %%
from colorspacious import cspace_convert

def simulate_cvd(rgb, deficiency="deuteranomaly", severity=70):
    """
    rgb: (..., 3) array in [0, 1]
    deficiency: 'protanomaly', 'deuteranomaly', 'tritanomaly'
    severity: 0–100
    """
    spec = {
        "name": "sRGB1+CVD",
        "cvd_type": deficiency,
        "severity": severity
    }
    return cspace_convert(rgb, spec,"sRGB1")

def show_cmap_cvd(cmap, deficiency):
    x = np.linspace(0, 1, 256)
    rgb = cmap(x)[:, :3]
    rgb_cvd = simulate_cvd(rgb, deficiency)
    return rgb_cvd

# %%
rgb_deut = show_cmap_cvd(soft_twilight, "deuteranomaly")
cmap_deut = LinearSegmentedColormap.from_list(
    "twilight_soft_cvd_deuteranomaly",
    rgb_deut.clip(0, 1)
)
cmap_deut
# %%
rgb_tritan = show_cmap_cvd(soft_twilight, "tritanomaly")
cmap_tritan = LinearSegmentedColormap.from_list(
    "twilight_soft_cvd_tritanomaly",
    rgb_tritan.clip(0, 1)
)
cmap_tritan
# %%
rgb_prot = show_cmap_cvd(soft_twilight, "protanomaly")
cmap_prot = LinearSegmentedColormap.from_list(
    "twilight_soft_cvd_protanomaly",
    rgb_prot.clip(0, 1)
)       
cmap_prot
# %%
# Pallette:
# https://coolors.co/77587e-7499c4-c2896c-c86c62-bd5172-797bd0-8fa9b5-b6aeb5-8958b4
def custom_colors():
    return [
        "#77587e",
        "#7499c4",
        "#c2896c",    
        "#c86c62",
        "#bd5172",
        "#797bd0",
        "#8fa9b5",
        "#b6aeb5",
        "#8958b4"
]  

colors = custom_colors()
colors
# %%

###### Difference #####

# Get the original colormap
cmap = soften_twilight_cam02()

# Number of colors in the new colormap
n = 256

# Sample the middle half of the colormap
colors = cmap(np.linspace(0.15, 0.85, n))

# Create a new colormap from the cropped colors
cropped_cmap = LinearSegmentedColormap.from_list('cropped_soft_twilight', colors)

cropped_cmap
# %%
