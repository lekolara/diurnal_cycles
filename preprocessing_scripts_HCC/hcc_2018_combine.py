import xarray as xr

""" this code combines the HCC data over the entire 2018 and saves it as .nc file """
ds = xr.concat(
    (
        xr.concat(
            (
                xr.open_dataset(f'hcc_2018/hcc_2018_{i_month}_0p{v:d}.zarr').compute()
                for i_month in range(1, 13)
            ),
            dim='time'
        )
        for v in [36, 50, 75, 90]
    ),
    dim='threshold'
)#.rename({'__xarray_dataarray_variable__': 'hcc'})

for v in ds.variables:
    try:
        ds[v].encoding = {}
    except Exception:
        pass

ds.to_netcdf('hcc_2018_all.nc')
ds.sel(threshold=[0.36]).to_netcdf('hcc_2018_opt.nc')
