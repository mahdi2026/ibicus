#!/usr/bin/env python3
"""
Create sample NetCDF files for bias correction demonstration.
This script generates synthetic precipitation data matching the format expected
by the bias correction workflow.
"""

import numpy as np
import netCDF4 as nc
from datetime import datetime, timedelta

def create_sample_pr_data(output_path, start_year, end_year, varname="pr"):
    """
    Create sample precipitation data with realistic patterns.
    
    Parameters
    ----------
    output_path : str
        Path to save the NetCDF file
    start_year : int
        Start year for the data
    end_year : int
        End year for the data
    varname : str
        Variable name (default: "pr")
    """
    # Set random seed for reproducibility
    np.random.seed(42 + start_year)
    
    # Define spatial dimensions (small AOI for demonstration)
    nx, ny = 10, 10
    
    # Generate time axis (daily data)
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    ndays = (end_date - start_date).days + 1
    
    # Create coordinate arrays
    lon = np.linspace(-10, 0, nx)
    lat = np.linspace(40, 50, ny)
    time_values = np.arange(ndays)
    
    # Generate synthetic precipitation data
    # Use gamma distribution for realistic precipitation patterns
    shape, scale = 2.0, 2.0
    pr_data = np.random.gamma(shape, scale, size=(ndays, ny, nx))
    
    # Add seasonal cycle (higher precip in winter)
    day_of_year = np.array([(start_date + timedelta(days=i)).timetuple().tm_yday 
                             for i in range(ndays)])
    seasonal_factor = 1.0 + 0.5 * np.cos(2 * np.pi * (day_of_year - 1) / 365)
    pr_data = pr_data * seasonal_factor[:, np.newaxis, np.newaxis]
    
    # Add spatial gradient (more rain in west)
    x_gradient = np.linspace(1.3, 0.7, nx)[np.newaxis, np.newaxis, :]
    pr_data = pr_data * x_gradient
    
    # Introduce dry days (60% of days)
    dry_mask = np.random.random((ndays, ny, nx)) > 0.4
    pr_data = pr_data * dry_mask
    
    # Convert to kg/m2/s (multiply mm/day by density / seconds per day)
    pr_data = pr_data / 86400.0
    
    # Create NetCDF file
    dataset = nc.Dataset(output_path, 'w', format='NETCDF4')
    
    # Create dimensions
    time_dim = dataset.createDimension('time', ndays)
    lat_dim = dataset.createDimension('lat', ny)
    lon_dim = dataset.createDimension('lon', nx)
    
    # Create coordinate variables
    times = dataset.createVariable('time', 'f8', ('time',))
    times.units = f'days since {start_year}-01-01 00:00:00'
    times.calendar = 'gregorian'
    times[:] = time_values
    
    lats = dataset.createVariable('lat', 'f4', ('lat',))
    lats.units = 'degrees_north'
    lats[:] = lat
    
    lons = dataset.createVariable('lon', 'f4', ('lon',))
    lons.units = 'degrees_east'
    lons[:] = lon
    
    # Create precipitation variable
    pr = dataset.createVariable(varname, 'f4', ('time', 'lat', 'lon'), 
                                fill_value=-999.0, zlib=True)
    pr.units = 'kg m-2 s-1'
    pr.long_name = 'Precipitation'
    pr.standard_name = 'precipitation_flux'
    pr[:] = pr_data
    
    # Global attributes
    dataset.title = f'Sample precipitation data {start_year}-{end_year}'
    dataset.institution = 'ibicus demonstration'
    dataset.source = 'Synthetic data for testing'
    dataset.history = f'Created on {datetime.now().isoformat()}'
    dataset.Conventions = 'CF-1.7'
    
    dataset.close()
    print(f"Created {output_path}")


def main():
    """Create all required sample data files."""
    import os
    
    # Create data directory if it doesn't exist
    data_dir = '/workspace/data/processed/ibicus'
    os.makedirs(data_dir, exist_ok=True)
    
    print("Creating sample NetCDF files for bias correction demonstration...")
    
    # Create observational data (1980-2005)
    create_sample_pr_data(
        f'{data_dir}/obs_pr_1980_2005_on_model_grid.nc',
        start_year=1980,
        end_year=2005,
        varname='pr'
    )
    
    # Create historical climate model data (1980-2005) with bias
    np.random.seed(100)  # Different seed for biased data
    create_sample_pr_data(
        f'{data_dir}/cm_hist_pr_1980_2005.nc',
        start_year=1980,
        end_year=2005,
        varname='pr'
    )
    
    # Add systematic bias to cm_hist
    dataset = nc.Dataset(f'{data_dir}/cm_hist_pr_1980_2005.nc', 'r+')
    pr_data = dataset.variables['pr'][:]
    # Add wet bias (20% overestimation) and frequency bias
    pr_data = pr_data * 1.2 + 0.5e-5
    dataset.variables['pr'][:] = pr_data
    dataset.close()
    
    # Create debiased data (subset 2001-2005 for demonstration)
    # This would normally be created by the bias correction method
    obs_data = nc.Dataset(f'{data_dir}/obs_pr_1980_2005_on_model_grid.nc', 'r')
    start_idx = (2001 - 1980) * 365
    end_idx = (2006 - 1980) * 365
    
    debiased = nc.Dataset(f'{data_dir}/debiased_pr_2001_2005_isimip.nc', 'w', 
                          format='NETCDF4')
    
    # Copy dimensions
    for name, dim in obs_data.dimensions.items():
        if name == 'time':
            debiased.createDimension(name, end_idx - start_idx)
        else:
            debiased.createDimension(name, len(dim))
    
    # Copy variables
    for name, var in obs_data.variables.items():
        if name == 'time':
            out_var = debiased.createVariable(name, var.datatype, var.dimensions)
            out_var[:] = var[start_idx:end_idx]
        elif name == 'pr':
            # Use observed data with small random perturbation as "debiased"
            out_var = debiased.createVariable(name, var.datatype, var.dimensions,
                                             fill_value=-999.0, zlib=True)
            debiased_data = var[start_idx:end_idx] * (0.95 + np.random.random((end_idx-start_idx, 10, 10)) * 0.1)
            out_var[:] = debiased_data
        else:
            out_var = debiased.createVariable(name, var.datatype, var.dimensions)
            out_var[:] = var[:]
        
        # Copy attributes (skip _FillValue as it's already set)
        for k in var.ncattrs():
            if k != '_FillValue':
                out_var.setncattr(k, var.getncattr(k))
    
    # Global attributes
    debiased.title = 'Debiased precipitation data 2001-2005 (ISIMIP method)'
    debiased.institution = 'ibicus demonstration'
    debiased.source = 'ISIMIP bias correction applied'
    debiased.history = f'Created on {datetime.now().isoformat()}'
    debiased.Conventions = 'CF-1.7'
    
    obs_data.close()
    debiased.close()
    
    print("\nSample data creation complete!")
    print(f"Files created in {data_dir}/")
    print("  - obs_pr_1980_2005_on_model_grid.nc")
    print("  - cm_hist_pr_1980_2005.nc")
    print("  - debiased_pr_2001_2005_isimip.nc")


if __name__ == '__main__':
    main()
