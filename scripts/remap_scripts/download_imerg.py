# %%
import earthaccess
import xarray as xr

# %%
# Downloading IMERG data from NASA Earthdata using EarthAccess
earthaccess.login() # You set up some credentials, but only once and are stored in ~/.netrc
nasa_status = earthaccess.status()
print(nasa_status)

date_start = "2022-01-01"
date_end = "2022-12-31"
#date_end = "2023-01-02"
date_range = (date_start, date_end)
#A bounding box is defined by lower left longitude, 
#lower left latitude, upper right longitude, upper right latitude.
bounding_box = (-180, -60, 180, 60) # Global
results = earthaccess.search_data(
    short_name = "GPM_3IMERGHH",
    version = "07",
    temporal=date_range, # For all data for 2023-01-01, for example
    bounding_box=bounding_box, # Optional spatial constraint
)

print(f"Total size {sum(r['size'] for r in results) / 1024:.2f} GiB")

# Download locally
filelist = earthaccess.download(results, '/scratch/leko/IMERG/GPM_3IMERGHH_2022', pqdm_kwargs={'ncols': 80})

# %%

# Comparing datasets
# ds1: Original HDF5 file from NASA i downloaded previously
# ds2: Converted NetCDF4 file from Gunnar Behrens, he had them already downloaded
ds1 = xr.open_dataset('/scratch/leko/IMERG/GPM_IMERG_raw/GPM_3IMERGHH_2023/3B-HHR.MS.MRG.3IMERG.20230712-S020000-E022959.0120.V07B.HDF5', group = 'Grid')
ds1
print("ds1 variables:", list(ds1.variables))
print("ds1 dimensions:", ds1.dims)
print("ds1 shape:", ds1.sizes)
print("\nds1 global attributes:", ds1.attrs)
for var in ds1.data_vars:
    print(f"ds1 variable '{var}' attributes:", ds1[var].attrs)

print("\nds1 time variable:", ds1['time'])
print("ds1 time dtype:", ds1['time'].dtype)
# %%
ds2 = xr.open_dataset('/scratch/leko/IMERG/G_Behrens_GPM_IMERG_raw/G_Behrens_GPM_IMERG_raw_2018/3B-HHR.MS.MRG.3IMERG.20181231-S233000-E235959.1410.V07B.HDF5.SUB.nc4')
ds2
print("ds2 variables:", list(ds2.variables))
print("ds2 dimensions:", ds2.dims)
print("ds2 shape:", ds2.sizes)
print("\nds2 global attributes:", ds2.attrs)
for var in ds2.data_vars:
    print(f"ds2 variable '{var}' attributes:", ds2[var].attrs)

print("\nds2 time variable:", ds2['time'])
print("ds2 time dtype:", ds2['time'].dtype)


# %%
# A function to convert IMERG HDF5 files to NetCDF4 format with compatible
# time format and reduced variables.
# I did this for 2022 and 2023 data.

from pathlib import Path

# Input and output directories
in_dir = Path('/scratch/leko/IMERG/GPM_IMERG_raw/GPM_3IMERGHH_2023/')
out_dir = Path('/scratch/leko/IMERG/GPM_IMERG_converted/GPM_3IMERGHH_2023_conv/')
out_dir.mkdir(exist_ok=True)

# Variables to keep to match Gunnar's dataset
keep_vars = ["precipitation"]

# Variables to remove from Earthacess dataset
drop_vars = [
    "randomError",
    "probabilityLiquidPrecipitation",
    "precipitationQualityIndex",
    "time_bnds",
    "lat_bnds",
    "lon_bnds",
]

def convert_file(infile, outfile):
    # Load ds1-style dataset WITHOUT decoding time
    # decode_times=False tells xarray not to interpret the time variable as actual timestamps when reading the file.
    # Otherwise it will convert it to cftime.DatetimeJulian
    ds = xr.open_dataset(infile, group  = 'Grid')


    # Convert cftime "seconds since 1980" to datetime64
    # ds.indexes is a dictionary-like object in xarray for the dimensions in the dataset
    # Can be compatible with pandas indexes
    ds["time"] = ds.indexes["time"].to_datetimeindex(time_unit="ns")
    
    # drop variables we don't need
    ds2 = ds.drop_vars(drop_vars, errors="ignore")
    
    # keep only precipitation variable
    ds2 = ds2[keep_vars]

    # save to NetCDF4
    ds2.to_netcdf(outfile, format="NETCDF4")


# Find all files from 2022–2023 (NetCDF or HDF5)
files = sorted(list(in_dir.glob("*2023*.HDF5")))

print(f"Found {len(files)} files to convert.")

# Convert each file
# f.stem is filename without extension

for f in files:
    outpath = out_dir / (f.stem + "_converted.nc")
    print(f"Converting {f.name} → {outpath.name}")
    convert_file(f, outpath)

print("Done.")

