#!/usr/bin/env python3
"""
Bias Correction Diagnostic Plots

This script generates comprehensive diagnostic visualizations for bias correction
evaluation, following best practices from the ibicus package.

References:
- ibicus: https://github.com/ecmwf-projects/ibicus
- Documentation: https://ibicus.readthedocs.io/en/latest/
- Paper: Spuler et al. 2024, GMD, doi:10.5194/gmd-17-1249-2024

Author: Climate Analysis Team
Date: 2025-10-01
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import netCDF4 as nc
from scipy import stats
import warnings

warnings.filterwarnings('ignore')

# Set publication-quality style
plt.style.use('seaborn-v0_8-paper')
sns.set_palette("colorblind")
plt.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.titlesize': 12,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

# Define paths
DATA_DIR = Path('/workspace/data/processed/ibicus')
FIG_DIR = Path('/workspace/data/processed/ibicus/figures')
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load observation, raw, and debiased precipitation data."""
    print("Loading data...")
    
    # Load observational data (full period for training)
    obs_file = DATA_DIR / 'obs_pr_1980_2005_on_model_grid.nc'
    obs_ds = nc.Dataset(obs_file, 'r')
    
    # Extract validation period (2001-2005) from obs for comparison
    start_idx = (2001 - 1980) * 365
    end_idx = (2006 - 1980) * 365
    obs_data = obs_ds.variables['pr'][start_idx:end_idx, :, :]
    obs_time = obs_ds.variables['time'][start_idx:end_idx]
    
    # Load raw climate model data (historical)
    raw_file = DATA_DIR / 'cm_hist_pr_1980_2005.nc'
    raw_ds = nc.Dataset(raw_file, 'r')
    raw_data = raw_ds.variables['pr'][start_idx:end_idx, :, :]
    
    # Load debiased data
    debiased_file = DATA_DIR / 'debiased_pr_2001_2005_isimip.nc'
    debiased_ds = nc.Dataset(debiased_file, 'r')
    debiased_data = debiased_ds.variables['pr'][:, :, :]
    
    # Get coordinates
    lat = obs_ds.variables['lat'][:]
    lon = obs_ds.variables['lon'][:]
    
    obs_ds.close()
    raw_ds.close()
    debiased_ds.close()
    
    print(f"  Obs shape: {obs_data.shape}")
    print(f"  Raw shape: {raw_data.shape}")
    print(f"  Debiased shape: {debiased_data.shape}")
    
    return obs_data, raw_data, debiased_data, lat, lon, obs_time


def convert_to_mm_day(pr_data):
    """Convert precipitation from kg/m2/s to mm/day."""
    # 1 kg/m2/s = 86400 mm/day
    return pr_data * 86400.0


def plot_histograms_and_ecdfs(obs, raw, debiased):
    """
    Plot histograms and empirical cumulative distribution functions.
    
    This is a key diagnostic to assess distributional alignment.
    """
    print("Creating histograms and ECDFs...")
    
    # Convert to mm/day and flatten spatial dimensions
    obs_flat = convert_to_mm_day(obs).flatten()
    raw_flat = convert_to_mm_day(raw).flatten()
    debiased_flat = convert_to_mm_day(debiased).flatten()
    
    # Remove zeros for better visualization
    obs_nonzero = obs_flat[obs_flat > 0.01]
    raw_nonzero = raw_flat[raw_flat > 0.01]
    debiased_nonzero = debiased_flat[debiased_flat > 0.01]
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Histogram - All data
    ax = axes[0, 0]
    bins = np.linspace(0, np.percentile(obs_flat, 99), 50)
    ax.hist(obs_flat, bins=bins, alpha=0.6, label='Observations', density=True, 
            color='blue', edgecolor='black', linewidth=0.5)
    ax.hist(raw_flat, bins=bins, alpha=0.5, label='Raw CM', density=True,
            color='red', edgecolor='black', linewidth=0.5)
    ax.hist(debiased_flat, bins=bins, alpha=0.5, label='Debiased (ISIMIP)', 
            density=True, color='green', edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Precipitation (mm/day)')
    ax.set_ylabel('Probability Density')
    ax.set_title('Distribution: All Data')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Histogram - Wet days only
    ax = axes[0, 1]
    bins = np.linspace(0, np.percentile(obs_nonzero, 99), 50)
    ax.hist(obs_nonzero, bins=bins, alpha=0.6, label='Observations', density=True,
            color='blue', edgecolor='black', linewidth=0.5)
    ax.hist(raw_nonzero, bins=bins, alpha=0.5, label='Raw CM', density=True,
            color='red', edgecolor='black', linewidth=0.5)
    ax.hist(debiased_nonzero, bins=bins, alpha=0.5, label='Debiased (ISIMIP)', 
            density=True, color='green', edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Precipitation (mm/day)')
    ax.set_ylabel('Probability Density')
    ax.set_title('Distribution: Wet Days Only (>0.01 mm/day)')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # ECDF - All data
    ax = axes[1, 0]
    sorted_obs = np.sort(obs_flat)
    sorted_raw = np.sort(raw_flat)
    sorted_debiased = np.sort(debiased_flat)
    
    ax.plot(sorted_obs, np.arange(len(sorted_obs)) / len(sorted_obs), 
            label='Observations', linewidth=2, color='blue')
    ax.plot(sorted_raw, np.arange(len(sorted_raw)) / len(sorted_raw),
            label='Raw CM', linewidth=2, color='red', alpha=0.7)
    ax.plot(sorted_debiased, np.arange(len(sorted_debiased)) / len(sorted_debiased),
            label='Debiased (ISIMIP)', linewidth=2, color='green', alpha=0.7)
    ax.set_xlabel('Precipitation (mm/day)')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('Empirical CDF: All Data')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0, np.percentile(obs_flat, 99))
    
    # ECDF - Wet days only (log scale)
    ax = axes[1, 1]
    sorted_obs = np.sort(obs_nonzero)
    sorted_raw = np.sort(raw_nonzero)
    sorted_debiased = np.sort(debiased_nonzero)
    
    ax.plot(sorted_obs, np.arange(len(sorted_obs)) / len(sorted_obs),
            label='Observations', linewidth=2, color='blue')
    ax.plot(sorted_raw, np.arange(len(sorted_raw)) / len(sorted_raw),
            label='Raw CM', linewidth=2, color='red', alpha=0.7)
    ax.plot(sorted_debiased, np.arange(len(sorted_debiased)) / len(sorted_debiased),
            label='Debiased (ISIMIP)', linewidth=2, color='green', alpha=0.7)
    ax.set_xlabel('Precipitation (mm/day)')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('Empirical CDF: Wet Days (log scale)')
    ax.set_xscale('log')
    ax.legend()
    ax.grid(alpha=0.3, which='both')
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '01_histograms_and_ecdfs.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '01_histograms_and_ecdfs.png'}")


def plot_qq_plots(obs, raw, debiased):
    """
    Create quantile-quantile plots comparing obs vs raw and obs vs debiased.
    
    QQ plots are essential for assessing bias correction performance across quantiles.
    """
    print("Creating QQ plots...")
    
    # Convert to mm/day and flatten
    obs_flat = convert_to_mm_day(obs).flatten()
    raw_flat = convert_to_mm_day(raw).flatten()
    debiased_flat = convert_to_mm_day(debiased).flatten()
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # QQ plot: Obs vs Raw
    ax = axes[0]
    quantiles = np.linspace(0, 1, 1000)
    obs_q = np.quantile(obs_flat, quantiles)
    raw_q = np.quantile(raw_flat, quantiles)
    
    ax.scatter(obs_q, raw_q, alpha=0.5, s=10, color='red', label='Raw CM')
    # 1:1 line
    max_val = max(obs_q.max(), raw_q.max())
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=1.5, label='1:1 line')
    ax.set_xlabel('Observed Quantiles (mm/day)')
    ax.set_ylabel('Model Quantiles (mm/day)')
    ax.set_title('QQ Plot: Observations vs. Raw CM')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Calculate and display bias statistics
    bias_mean = np.mean(raw_q - obs_q)
    bias_p95 = raw_q[950] - obs_q[950]  # 95th percentile
    ax.text(0.05, 0.95, f'Mean bias: {bias_mean:.3f} mm/day\n95th pct bias: {bias_p95:.3f} mm/day',
            transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # QQ plot: Obs vs Debiased
    ax = axes[1]
    debiased_q = np.quantile(debiased_flat, quantiles)
    
    ax.scatter(obs_q, debiased_q, alpha=0.5, s=10, color='green', label='Debiased (ISIMIP)')
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=1.5, label='1:1 line')
    ax.set_xlabel('Observed Quantiles (mm/day)')
    ax.set_ylabel('Model Quantiles (mm/day)')
    ax.set_title('QQ Plot: Observations vs. Debiased CM')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Calculate and display bias statistics
    bias_mean = np.mean(debiased_q - obs_q)
    bias_p95 = debiased_q[950] - obs_q[950]
    ax.text(0.05, 0.95, f'Mean bias: {bias_mean:.3f} mm/day\n95th pct bias: {bias_p95:.3f} mm/day',
            transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '02_qq_plots.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '02_qq_plots.png'}")


def plot_seasonal_cycle(obs, raw, debiased, time_values):
    """
    Plot monthly mean precipitation to assess seasonal patterns.
    
    Seasonal cycle evaluation is important for climate applications.
    """
    print("Creating seasonal cycle plot...")
    
    # Convert to mm/day
    obs_mm = convert_to_mm_day(obs)
    raw_mm = convert_to_mm_day(raw)
    debiased_mm = convert_to_mm_day(debiased)
    
    # Compute spatial mean for each time step
    obs_mean = np.mean(obs_mm, axis=(1, 2))
    raw_mean = np.mean(raw_mm, axis=(1, 2))
    debiased_mean = np.mean(debiased_mm, axis=(1, 2))
    
    # Group by month (assuming daily data for 5 years: 2001-2005)
    # Simple approach: use day of year
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Initialize monthly arrays
    n_years = 5
    obs_monthly = np.zeros((n_years, 12))
    raw_monthly = np.zeros((n_years, 12))
    debiased_monthly = np.zeros((n_years, 12))
    
    # Fill monthly means
    day_idx = 0
    for year in range(n_years):
        for month in range(12):
            days = days_per_month[month]
            if month == 1 and year % 4 == 1:  # Leap year adjustment
                days = 29
            
            obs_monthly[year, month] = np.mean(obs_mean[day_idx:day_idx + days])
            raw_monthly[year, month] = np.mean(raw_mean[day_idx:day_idx + days])
            debiased_monthly[year, month] = np.mean(debiased_mean[day_idx:day_idx + days])
            day_idx += days
    
    # Compute climatology (mean over years)
    obs_clim = np.mean(obs_monthly, axis=0)
    raw_clim = np.mean(raw_monthly, axis=0)
    debiased_clim = np.mean(debiased_monthly, axis=0)
    
    # Compute standard error
    obs_se = np.std(obs_monthly, axis=0) / np.sqrt(n_years)
    raw_se = np.std(raw_monthly, axis=0) / np.sqrt(n_years)
    debiased_se = np.std(debiased_monthly, axis=0) / np.sqrt(n_years)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    x = np.arange(12)
    
    ax.plot(x, obs_clim, 'o-', linewidth=2, label='Observations', color='blue')
    ax.fill_between(x, obs_clim - obs_se, obs_clim + obs_se, alpha=0.2, color='blue')
    
    ax.plot(x, raw_clim, 's-', linewidth=2, label='Raw CM', color='red', alpha=0.7)
    ax.fill_between(x, raw_clim - raw_se, raw_clim + raw_se, alpha=0.2, color='red')
    
    ax.plot(x, debiased_clim, '^-', linewidth=2, label='Debiased (ISIMIP)', 
            color='green', alpha=0.7)
    ax.fill_between(x, debiased_clim - debiased_se, debiased_clim + debiased_se,
                     alpha=0.2, color='green')
    
    ax.set_xticks(x)
    ax.set_xticklabels(months)
    ax.set_xlabel('Month')
    ax.set_ylabel('Mean Precipitation (mm/day)')
    ax.set_title('Seasonal Cycle of Precipitation (2001-2005)')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '03_seasonal_cycle.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '03_seasonal_cycle.png'}")


def plot_wet_day_frequency(obs, raw, debiased):
    """
    Bar plot of wet-day frequency (days with precipitation > threshold).
    
    Wet-day frequency is a critical metric for precipitation bias correction.
    """
    print("Creating wet-day frequency plot...")
    
    # Convert to mm/day
    obs_mm = convert_to_mm_day(obs)
    raw_mm = convert_to_mm_day(raw)
    debiased_mm = convert_to_mm_day(debiased)
    
    # Define thresholds
    thresholds = [0.1, 1.0, 10.0, 20.0]  # mm/day
    threshold_names = ['Trace (>0.1)', 'Light (>1)', 'Heavy (>10)', 'Extreme (>20)']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(thresholds))
    width = 0.25
    
    obs_freq = []
    raw_freq = []
    debiased_freq = []
    
    for thresh in thresholds:
        # Compute frequency as percentage of all days
        obs_freq.append(100 * np.mean(obs_mm > thresh))
        raw_freq.append(100 * np.mean(raw_mm > thresh))
        debiased_freq.append(100 * np.mean(debiased_mm > thresh))
    
    bars1 = ax.bar(x - width, obs_freq, width, label='Observations', color='blue')
    bars2 = ax.bar(x, raw_freq, width, label='Raw CM', color='red', alpha=0.7)
    bars3 = ax.bar(x + width, debiased_freq, width, label='Debiased (ISIMIP)', 
                   color='green', alpha=0.7)
    
    # Add value labels on bars
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=8)
    
    autolabel(bars1)
    autolabel(bars2)
    autolabel(bars3)
    
    ax.set_xlabel('Precipitation Threshold (mm/day)')
    ax.set_ylabel('Frequency (%)')
    ax.set_title('Wet-Day Frequency by Threshold')
    ax.set_xticks(x)
    ax.set_xticklabels(threshold_names)
    ax.legend()
    ax.grid(alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '04_wet_day_frequency.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '04_wet_day_frequency.png'}")


def plot_extreme_tails(obs, raw, debiased):
    """
    Compare extreme precipitation (95th and 99th percentiles) spatially.
    
    Extreme values are often poorly simulated and critical for impact assessment.
    """
    print("Creating extreme precipitation comparison...")
    
    # Convert to mm/day
    obs_mm = convert_to_mm_day(obs)
    raw_mm = convert_to_mm_day(raw)
    debiased_mm = convert_to_mm_day(debiased)
    
    # Compute percentiles at each grid point
    obs_p95 = np.percentile(obs_mm, 95, axis=0)
    raw_p95 = np.percentile(raw_mm, 95, axis=0)
    debiased_p95 = np.percentile(debiased_mm, 95, axis=0)
    
    obs_p99 = np.percentile(obs_mm, 99, axis=0)
    raw_p99 = np.percentile(raw_mm, 99, axis=0)
    debiased_p99 = np.percentile(debiased_mm, 99, axis=0)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Define common colorbar range
    vmin_95 = min(obs_p95.min(), raw_p95.min(), debiased_p95.min())
    vmax_95 = max(obs_p95.max(), raw_p95.max(), debiased_p95.max())
    
    vmin_99 = min(obs_p99.min(), raw_p99.min(), debiased_p99.min())
    vmax_99 = max(obs_p99.max(), raw_p99.max(), debiased_p99.max())
    
    # 95th percentile maps
    im1 = axes[0, 0].imshow(obs_p95, cmap='Blues', vmin=vmin_95, vmax=vmax_95)
    axes[0, 0].set_title('Obs: 95th Percentile')
    axes[0, 0].set_xlabel('Longitude index')
    axes[0, 0].set_ylabel('Latitude index')
    plt.colorbar(im1, ax=axes[0, 0], label='mm/day')
    
    im2 = axes[0, 1].imshow(raw_p95, cmap='Blues', vmin=vmin_95, vmax=vmax_95)
    axes[0, 1].set_title('Raw CM: 95th Percentile')
    axes[0, 1].set_xlabel('Longitude index')
    axes[0, 1].set_ylabel('Latitude index')
    plt.colorbar(im2, ax=axes[0, 1], label='mm/day')
    
    im3 = axes[0, 2].imshow(debiased_p95, cmap='Blues', vmin=vmin_95, vmax=vmax_95)
    axes[0, 2].set_title('Debiased: 95th Percentile')
    axes[0, 2].set_xlabel('Longitude index')
    axes[0, 2].set_ylabel('Latitude index')
    plt.colorbar(im3, ax=axes[0, 2], label='mm/day')
    
    # 99th percentile maps
    im4 = axes[1, 0].imshow(obs_p99, cmap='Reds', vmin=vmin_99, vmax=vmax_99)
    axes[1, 0].set_title('Obs: 99th Percentile')
    axes[1, 0].set_xlabel('Longitude index')
    axes[1, 0].set_ylabel('Latitude index')
    plt.colorbar(im4, ax=axes[1, 0], label='mm/day')
    
    im5 = axes[1, 1].imshow(raw_p99, cmap='Reds', vmin=vmin_99, vmax=vmax_99)
    axes[1, 1].set_title('Raw CM: 99th Percentile')
    axes[1, 1].set_xlabel('Longitude index')
    axes[1, 1].set_ylabel('Latitude index')
    plt.colorbar(im5, ax=axes[1, 1], label='mm/day')
    
    im6 = axes[1, 2].imshow(debiased_p99, cmap='Reds', vmin=vmin_99, vmax=vmax_99)
    axes[1, 2].set_title('Debiased: 99th Percentile')
    axes[1, 2].set_xlabel('Longitude index')
    axes[1, 2].set_ylabel('Latitude index')
    plt.colorbar(im6, ax=axes[1, 2], label='mm/day')
    
    plt.suptitle('Extreme Precipitation Comparison (P95 and P99)', fontsize=14, y=0.995)
    plt.tight_layout()
    plt.savefig(FIG_DIR / '05_extreme_percentiles_maps.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '05_extreme_percentiles_maps.png'}")


def plot_timeseries_sample(obs, raw, debiased):
    """
    Plot time series for a representative grid point.
    
    Time series help visualize temporal behavior and bias correction impact.
    """
    print("Creating sample time series...")
    
    # Select central grid point
    nlat, nlon = obs.shape[1], obs.shape[2]
    i, j = nlat // 2, nlon // 2
    
    # Convert to mm/day
    obs_ts = convert_to_mm_day(obs[:, i, j])
    raw_ts = convert_to_mm_day(raw[:, i, j])
    debiased_ts = convert_to_mm_day(debiased[:, i, j])
    
    # Plot full time series (first 365 days only for visibility)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    # First year
    days = np.arange(365)
    ax = axes[0]
    ax.plot(days, obs_ts[:365], 'o-', linewidth=1, markersize=2, 
            label='Observations', color='blue', alpha=0.7)
    ax.plot(days, raw_ts[:365], 's-', linewidth=1, markersize=2,
            label='Raw CM', color='red', alpha=0.7)
    ax.plot(days, debiased_ts[:365], '^-', linewidth=1, markersize=2,
            label='Debiased (ISIMIP)', color='green', alpha=0.7)
    ax.set_xlabel('Day of Year')
    ax.set_ylabel('Precipitation (mm/day)')
    ax.set_title(f'Daily Precipitation Time Series: Year 2001 (Grid point [{i}, {j}])')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Rolling mean (30-day window) for full period
    ax = axes[1]
    window = 30
    obs_smooth = np.convolve(obs_ts, np.ones(window)/window, mode='valid')
    raw_smooth = np.convolve(raw_ts, np.ones(window)/window, mode='valid')
    debiased_smooth = np.convolve(debiased_ts, np.ones(window)/window, mode='valid')
    
    days_smooth = np.arange(len(obs_smooth))
    ax.plot(days_smooth, obs_smooth, linewidth=2, label='Observations', color='blue')
    ax.plot(days_smooth, raw_smooth, linewidth=2, label='Raw CM', color='red', alpha=0.7)
    ax.plot(days_smooth, debiased_smooth, linewidth=2, label='Debiased (ISIMIP)', 
            color='green', alpha=0.7)
    ax.set_xlabel('Days since 2001-01-01')
    ax.set_ylabel('Precipitation (mm/day)')
    ax.set_title(f'30-Day Rolling Mean: Full Period 2001-2005 (Grid point [{i}, {j}])')
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '06_timeseries_sample_point.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '06_timeseries_sample_point.png'}")


def plot_scatter_comparison(obs, raw, debiased):
    """
    Scatter plots comparing observed vs modeled values with 1:1 line.
    
    Scatter plots provide a direct visual assessment of bias correction performance.
    """
    print("Creating scatter comparison plots...")
    
    # Convert to mm/day and flatten
    obs_flat = convert_to_mm_day(obs).flatten()
    raw_flat = convert_to_mm_day(raw).flatten()
    debiased_flat = convert_to_mm_day(debiased).flatten()
    
    # Subsample for visualization (too many points)
    n_sample = min(10000, len(obs_flat))
    idx = np.random.choice(len(obs_flat), n_sample, replace=False)
    
    obs_sample = obs_flat[idx]
    raw_sample = raw_flat[idx]
    debiased_sample = debiased_flat[idx]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Obs vs Raw
    ax = axes[0]
    ax.hexbin(obs_sample, raw_sample, gridsize=50, cmap='Reds', mincnt=1, 
              bins='log', alpha=0.8)
    
    # 1:1 line
    max_val = max(obs_sample.max(), raw_sample.max())
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=2, label='1:1 line')
    
    # Calculate R² and bias
    mask = (obs_sample > 0.01) & (raw_sample > 0.01)
    if mask.sum() > 10:
        r2 = np.corrcoef(obs_sample[mask], raw_sample[mask])[0, 1]**2
        bias = np.mean(raw_sample[mask] - obs_sample[mask])
        rmse = np.sqrt(np.mean((raw_sample[mask] - obs_sample[mask])**2))
        ax.text(0.05, 0.95, f'R² = {r2:.3f}\nBias = {bias:.3f} mm/day\nRMSE = {rmse:.3f} mm/day',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    ax.set_xlabel('Observed Precipitation (mm/day)')
    ax.set_ylabel('Raw CM Precipitation (mm/day)')
    ax.set_title('Observations vs. Raw Climate Model')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0, np.percentile(obs_sample, 99))
    ax.set_ylim(0, np.percentile(raw_sample, 99))
    
    # Obs vs Debiased
    ax = axes[1]
    ax.hexbin(obs_sample, debiased_sample, gridsize=50, cmap='Greens', mincnt=1,
              bins='log', alpha=0.8)
    
    ax.plot([0, max_val], [0, max_val], 'k--', linewidth=2, label='1:1 line')
    
    # Calculate R² and bias
    mask = (obs_sample > 0.01) & (debiased_sample > 0.01)
    if mask.sum() > 10:
        r2 = np.corrcoef(obs_sample[mask], debiased_sample[mask])[0, 1]**2
        bias = np.mean(debiased_sample[mask] - obs_sample[mask])
        rmse = np.sqrt(np.mean((debiased_sample[mask] - obs_sample[mask])**2))
        ax.text(0.05, 0.95, f'R² = {r2:.3f}\nBias = {bias:.3f} mm/day\nRMSE = {rmse:.3f} mm/day',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    ax.set_xlabel('Observed Precipitation (mm/day)')
    ax.set_ylabel('Debiased CM Precipitation (mm/day)')
    ax.set_title('Observations vs. Debiased Climate Model (ISIMIP)')
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_xlim(0, np.percentile(obs_sample, 99))
    ax.set_ylim(0, np.percentile(debiased_sample, 99))
    
    plt.tight_layout()
    plt.savefig(FIG_DIR / '07_scatter_comparison.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '07_scatter_comparison.png'}")


def plot_bias_maps(obs, raw, debiased):
    """
    Create spatial bias maps showing mean bias and relative bias.
    """
    print("Creating spatial bias maps...")
    
    # Convert to mm/day
    obs_mm = convert_to_mm_day(obs)
    raw_mm = convert_to_mm_day(raw)
    debiased_mm = convert_to_mm_day(debiased)
    
    # Compute temporal means
    obs_mean = np.mean(obs_mm, axis=0)
    raw_mean = np.mean(raw_mm, axis=0)
    debiased_mean = np.mean(debiased_mm, axis=0)
    
    # Compute biases
    raw_bias = raw_mean - obs_mean
    debiased_bias = debiased_mean - obs_mean
    
    # Relative bias (percent)
    raw_rel_bias = 100 * raw_bias / (obs_mean + 1e-6)
    debiased_rel_bias = 100 * debiased_bias / (obs_mean + 1e-6)
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    # Mean precipitation maps
    vmin = min(obs_mean.min(), raw_mean.min(), debiased_mean.min())
    vmax = max(obs_mean.max(), raw_mean.max(), debiased_mean.max())
    
    im1 = axes[0, 0].imshow(obs_mean, cmap='Blues', vmin=vmin, vmax=vmax)
    axes[0, 0].set_title('Observations: Mean')
    axes[0, 0].set_xlabel('Longitude index')
    axes[0, 0].set_ylabel('Latitude index')
    plt.colorbar(im1, ax=axes[0, 0], label='mm/day')
    
    im2 = axes[0, 1].imshow(raw_mean, cmap='Blues', vmin=vmin, vmax=vmax)
    axes[0, 1].set_title('Raw CM: Mean')
    axes[0, 1].set_xlabel('Longitude index')
    axes[0, 1].set_ylabel('Latitude index')
    plt.colorbar(im2, ax=axes[0, 1], label='mm/day')
    
    im3 = axes[0, 2].imshow(debiased_mean, cmap='Blues', vmin=vmin, vmax=vmax)
    axes[0, 2].set_title('Debiased: Mean')
    axes[0, 2].set_xlabel('Longitude index')
    axes[0, 2].set_ylabel('Latitude index')
    plt.colorbar(im3, ax=axes[0, 2], label='mm/day')
    
    # Absolute bias maps
    bias_max = max(abs(raw_bias.min()), abs(raw_bias.max()),
                   abs(debiased_bias.min()), abs(debiased_bias.max()))
    
    axes[1, 0].axis('off')  # Empty subplot
    
    im4 = axes[1, 1].imshow(raw_bias, cmap='RdBu_r', vmin=-bias_max, vmax=bias_max)
    axes[1, 1].set_title('Raw CM: Bias (Raw - Obs)')
    axes[1, 1].set_xlabel('Longitude index')
    axes[1, 1].set_ylabel('Latitude index')
    plt.colorbar(im4, ax=axes[1, 1], label='mm/day')
    
    im5 = axes[1, 2].imshow(debiased_bias, cmap='RdBu_r', vmin=-bias_max, vmax=bias_max)
    axes[1, 2].set_title('Debiased: Bias (Debiased - Obs)')
    axes[1, 2].set_xlabel('Longitude index')
    axes[1, 2].set_ylabel('Latitude index')
    plt.colorbar(im5, ax=axes[1, 2], label='mm/day')
    
    plt.suptitle('Mean Precipitation and Bias Maps', fontsize=14, y=0.995)
    plt.tight_layout()
    plt.savefig(FIG_DIR / '08_spatial_bias_maps.png')
    plt.close()
    print(f"  Saved: {FIG_DIR / '08_spatial_bias_maps.png'}")


def create_figures_index():
    """Create a markdown index of all generated figures."""
    print("Creating figures index...")
    
    figures = [
        ('01_histograms_and_ecdfs.png', 
         'Histograms and Empirical Cumulative Distribution Functions',
         'Comparison of probability distributions for all data and wet days only. '
         'ECDFs show how well the bias correction matches the observed distribution.'),
        
        ('02_qq_plots.png',
         'Quantile-Quantile (QQ) Plots',
         'QQ plots comparing observed vs. raw and observed vs. debiased quantiles. '
         'Points on the 1:1 line indicate perfect agreement.'),
        
        ('03_seasonal_cycle.png',
         'Seasonal Cycle of Precipitation',
         'Monthly mean precipitation climatology (2001-2005) showing seasonal patterns. '
         'Shaded areas represent standard error across years.'),
        
        ('04_wet_day_frequency.png',
         'Wet-Day Frequency by Threshold',
         'Frequency of days exceeding different precipitation thresholds. '
         'Critical for assessing bias correction of precipitation occurrence.'),
        
        ('05_extreme_percentiles_maps.png',
         'Extreme Precipitation (P95 and P99)',
         'Spatial distribution of 95th and 99th percentile precipitation. '
         'Extreme values are often challenging for climate models.'),
        
        ('06_timeseries_sample_point.png',
         'Time Series at Representative Point',
         'Daily precipitation and 30-day rolling mean for a central grid point. '
         'Illustrates temporal variability and bias correction smoothness.'),
        
        ('07_scatter_comparison.png',
         'Scatter Plots: Observed vs. Modeled',
         'Hexbin scatter plots with 1:1 reference line. Includes R², bias, and RMSE statistics. '
         'Log-scaled color shows density of points.'),
        
        ('08_spatial_bias_maps.png',
         'Spatial Bias Maps',
         'Mean precipitation and absolute bias (model - observations) maps. '
         'Shows spatial structure of biases before and after correction.'),
    ]
    
    index_content = f"""# Bias Correction Diagnostic Figures

Generated: {np.datetime64('today')}

## Overview

This directory contains comprehensive diagnostic plots for evaluating bias correction
performance using the **ISIMIP method** from the ibicus package.

**Dataset**: Precipitation (pr) validation period 2001-2005

**Method**: ISIMIP (Lange 2021) - trend-preserving parametric quantile mapping

**References**:
- ibicus repository: [https://github.com/ecmwf-projects/ibicus](https://github.com/ecmwf-projects/ibicus)
- Documentation: [https://ibicus.readthedocs.io/en/latest/](https://ibicus.readthedocs.io/en/latest/)
- Paper: Spuler et al. 2024, Geoscientific Model Development, doi:[10.5194/gmd-17-1249-2024](https://doi.org/10.5194/gmd-17-1249-2024)

## Diagnostic Figures

"""
    
    for i, (filename, title, description) in enumerate(figures, 1):
        index_content += f"""### {i}. {title}

**File**: `{filename}`

{description}

![{title}]({filename})

---

"""
    
    index_content += """
## Interpretation Guidelines

### Key Metrics for Success:

1. **Distribution Alignment** (Histograms/ECDFs): Debiased distribution should closely match observations
2. **QQ Plots**: Points should cluster near the 1:1 line across all quantiles
3. **Seasonal Cycle**: Debiased monthly means should track observations
4. **Wet-Day Frequency**: Critical for precipitation - frequencies should match observations
5. **Extremes**: P95/P99 should be corrected without introducing artifacts
6. **Temporal Coherence**: Time series should maintain realistic variability
7. **Spatial Patterns**: Bias maps should show reduced systematic errors

### Known Limitations:

- Bias correction cannot add information not present in observations
- Assumes stationarity of bias between training and application periods
- Spatial correlation structure may be imperfectly preserved
- Extreme events beyond observed range are extrapolated

## Methods Summary

### ISIMIP (Hempel et al. 2013, Lange 2019, 2021)

- **Type**: Parametric quantile mapping with trend preservation
- **Distribution**: Precipitation modeled with left-censored Gamma
- **Temporal**: Running 31-day window for seasonal variation
- **Extremes**: Additive correction for highest quantiles
- **Trend**: Explicitly preserves climate change signal

### Why CDFt Failed

The CDF-transform (CDFt) method encountered "Quantiles must be in the range [0, 1]" errors,
likely due to:
- Extreme values or numerical precision issues in ECDF estimation
- Insufficient handling of zero-inflated precipitation data
- Edge cases in the time-evolving quantile mapping

## Next Steps

1. Apply ISIMIP to full future projection period (e.g., 2006-2100)
2. Evaluate additional metrics (spell lengths, spatial correlation, multivariate dependencies)
3. Document any remaining biases for downstream impact modeling
4. Consider ensemble of methods if uncertainty quantification is needed

---

*Generated with `plot_bias_correction_diagnostics.py`*
"""
    
    index_path = FIG_DIR / 'figures_index.md'
    with open(index_path, 'w') as f:
        f.write(index_content)
    
    print(f"  Saved: {index_path}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("BIAS CORRECTION DIAGNOSTIC PLOTS")
    print("=" * 70)
    print()
    print("References:")
    print("  - ibicus: https://github.com/ecmwf-projects/ibicus")
    print("  - Docs: https://ibicus.readthedocs.io/en/latest/")
    print("  - Paper: Spuler et al. 2024, GMD, doi:10.5194/gmd-17-1249-2024")
    print()
    print("=" * 70)
    print()
    
    # Load data
    obs, raw, debiased, lat, lon, time_vals = load_data()
    
    print()
    print("Generating diagnostic plots...")
    print("-" * 70)
    
    # Generate all diagnostic plots
    plot_histograms_and_ecdfs(obs, raw, debiased)
    plot_qq_plots(obs, raw, debiased)
    plot_seasonal_cycle(obs, raw, debiased, time_vals)
    plot_wet_day_frequency(obs, raw, debiased)
    plot_extreme_tails(obs, raw, debiased)
    plot_timeseries_sample(obs, raw, debiased)
    plot_scatter_comparison(obs, raw, debiased)
    plot_bias_maps(obs, raw, debiased)
    
    # Create index
    print()
    print("-" * 70)
    create_figures_index()
    
    print()
    print("=" * 70)
    print("COMPLETED SUCCESSFULLY!")
    print(f"All figures saved to: {FIG_DIR}")
    print("See figures_index.md for detailed descriptions")
    print("=" * 70)


if __name__ == '__main__':
    main()
