#!/usr/bin/env python3
"""
Bias Correction Diagnostic Plots

This script generates comprehensive diagnostic plots for evaluating bias correction methods,
following the ibicus framework and examples. It produces plots consistent with the 
ibicus evaluation module for assessing the performance of bias adjustment methods.

References:
- GitHub: https://github.com/ecmwf-projects/ibicus
- Docs: https://ibicus.readthedocs.io/en/latest/
- Paper: Spuler et al. 2024, GMD, doi: 10.5194/gmd-17-1249-2024

Author: Generated for bias correction evaluation
Date: 2025-10-01
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import xarray as xr
from pathlib import Path
import warnings
from scipy import stats
from datetime import datetime
import matplotlib.dates as mdates

# Set style for publication-quality plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("colorblind")

class BiasCorrectionDiagnostics:
    """
    Class for generating comprehensive bias correction diagnostic plots
    following ibicus framework and best practices.
    """
    
    def __init__(self, output_dir="data/processed/ibicus/figures"):
        """
        Initialize the diagnostics class.
        
        Parameters
        ----------
        output_dir : str
            Directory to save output figures
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_created = []
        
    def load_data(self, obs_file=None, cm_hist_file=None, debiased_file=None):
        """
        Load observational, climate model historical, and debiased data.
        
        Parameters
        ----------
        obs_file : str
            Path to observational data file
        cm_hist_file : str  
            Path to climate model historical data file
        debiased_file : str
            Path to debiased data file
            
        Returns
        -------
        dict
            Dictionary containing loaded datasets
        """
        data = {}
        
        # For demonstration, create synthetic data if files don't exist
        if not all([obs_file, cm_hist_file, debiased_file]):
            print("Creating synthetic demonstration data...")
            data = self._create_synthetic_data()
        else:
            # Load actual NetCDF files
            try:
                data['obs'] = xr.open_dataset(obs_file)
                data['cm_hist'] = xr.open_dataset(cm_hist_file) 
                data['debiased'] = xr.open_dataset(debiased_file)
                print(f"Loaded data from: {obs_file}, {cm_hist_file}, {debiased_file}")
            except Exception as e:
                print(f"Error loading data: {e}")
                print("Creating synthetic demonstration data instead...")
                data = self._create_synthetic_data()
                
        return data
    
    def _create_synthetic_data(self):
        """Create synthetic data for demonstration purposes."""
        np.random.seed(42)
        
        # Create time series (5 years of daily data)
        n_days = 5 * 365
        time = pd.date_range('2001-01-01', periods=n_days, freq='D')
        
        # Create spatial grid (15x15 for demonstration)
        nx, ny = 15, 15
        
        # Generate synthetic precipitation data with realistic characteristics
        # Observational data (reference)
        obs_base = np.random.gamma(2, 2, (n_days, nx, ny))  # Gamma distribution for precip
        obs_seasonal = 1 + 0.5 * np.sin(2 * np.pi * np.arange(n_days) / 365)[:, None, None]
        obs_data = obs_base * obs_seasonal
        
        # Add dry days (zero precipitation)
        dry_prob = 0.6  # 60% dry days
        dry_mask = np.random.random((n_days, nx, ny)) < dry_prob
        obs_data[dry_mask] = 0
        
        # Climate model historical data (biased)
        cm_hist_data = obs_data * 1.2 + np.random.normal(0, 0.5, obs_data.shape)  # Wet bias
        cm_hist_data = np.maximum(cm_hist_data, 0)  # No negative precip
        
        # Debiased data (closer to observations)
        debiased_data = obs_data * 1.05 + np.random.normal(0, 0.2, obs_data.shape)
        debiased_data = np.maximum(debiased_data, 0)
        
        # Create xarray datasets
        coords = {
            'time': time,
            'x': np.arange(nx),
            'y': np.arange(ny)
        }
        
        data = {
            'obs': xr.Dataset({'pr': (['time', 'x', 'y'], obs_data)}, coords=coords),
            'cm_hist': xr.Dataset({'pr': (['time', 'x', 'y'], cm_hist_data)}, coords=coords),
            'debiased': xr.Dataset({'pr': (['time', 'x', 'y'], debiased_data)}, coords=coords)
        }
        
        return data
    
    def plot_histograms_and_ecdfs(self, data, variable='pr'):
        """
        Plot histograms and empirical cumulative distribution functions.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Extract data for a representative grid point
        obs_vals = data['obs'][variable].isel(x=7, y=7).values
        cm_hist_vals = data['cm_hist'][variable].isel(x=7, y=7).values
        debiased_vals = data['debiased'][variable].isel(x=7, y=7).values
        
        # Remove zeros for better visualization of wet days
        obs_wet = obs_vals[obs_vals > 0.1]
        cm_hist_wet = cm_hist_vals[cm_hist_vals > 0.1]
        debiased_wet = debiased_vals[debiased_vals > 0.1]
        
        # Histogram - All values
        axes[0, 0].hist(obs_vals, bins=50, alpha=0.7, label='Observations', density=True)
        axes[0, 0].hist(cm_hist_vals, bins=50, alpha=0.7, label='Raw Model', density=True)
        axes[0, 0].hist(debiased_vals, bins=50, alpha=0.7, label='Debiased', density=True)
        axes[0, 0].set_xlabel('Precipitation (mm/day)')
        axes[0, 0].set_ylabel('Density')
        axes[0, 0].set_title('Distribution - All Values')
        axes[0, 0].legend()
        axes[0, 0].set_xlim(0, 20)
        
        # Histogram - Wet days only
        axes[0, 1].hist(obs_wet, bins=30, alpha=0.7, label='Observations', density=True)
        axes[0, 1].hist(cm_hist_wet, bins=30, alpha=0.7, label='Raw Model', density=True)
        axes[0, 1].hist(debiased_wet, bins=30, alpha=0.7, label='Debiased', density=True)
        axes[0, 1].set_xlabel('Precipitation (mm/day)')
        axes[0, 1].set_ylabel('Density')
        axes[0, 1].set_title('Distribution - Wet Days Only (>0.1 mm/day)')
        axes[0, 1].legend()
        
        # ECDF - All values
        obs_sorted = np.sort(obs_vals)
        cm_hist_sorted = np.sort(cm_hist_vals)
        debiased_sorted = np.sort(debiased_vals)
        
        n = len(obs_vals)
        ecdf_y = np.arange(1, n + 1) / n
        
        axes[1, 0].plot(obs_sorted, ecdf_y, label='Observations', linewidth=2)
        axes[1, 0].plot(cm_hist_sorted, ecdf_y, label='Raw Model', linewidth=2)
        axes[1, 0].plot(debiased_sorted, ecdf_y, label='Debiased', linewidth=2)
        axes[1, 0].set_xlabel('Precipitation (mm/day)')
        axes[1, 0].set_ylabel('Cumulative Probability')
        axes[1, 0].set_title('Empirical CDF - All Values')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].set_xlim(0, 20)
        
        # ECDF - Wet days only
        obs_wet_sorted = np.sort(obs_wet)
        cm_hist_wet_sorted = np.sort(cm_hist_wet)
        debiased_wet_sorted = np.sort(debiased_wet)
        
        n_wet_obs = len(obs_wet)
        n_wet_cm = len(cm_hist_wet)
        n_wet_deb = len(debiased_wet)
        
        axes[1, 1].plot(obs_wet_sorted, np.arange(1, n_wet_obs + 1) / n_wet_obs, 
                       label='Observations', linewidth=2)
        axes[1, 1].plot(cm_hist_wet_sorted, np.arange(1, n_wet_cm + 1) / n_wet_cm, 
                       label='Raw Model', linewidth=2)
        axes[1, 1].plot(debiased_wet_sorted, np.arange(1, n_wet_deb + 1) / n_wet_deb, 
                       label='Debiased', linewidth=2)
        axes[1, 1].set_xlabel('Precipitation (mm/day)')
        axes[1, 1].set_ylabel('Cumulative Probability')
        axes[1, 1].set_title('Empirical CDF - Wet Days Only')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'histograms_and_ecdfs.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_qq_plots(self, data, variable='pr'):
        """
        Plot quantile-quantile plots comparing distributions.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Extract data for a representative grid point
        obs_vals = data['obs'][variable].isel(x=7, y=7).values
        cm_hist_vals = data['cm_hist'][variable].isel(x=7, y=7).values
        debiased_vals = data['debiased'][variable].isel(x=7, y=7).values
        
        # QQ plot: Observations vs Raw Model
        stats.probplot(cm_hist_vals, dist=stats.norm, sparams=(np.mean(obs_vals), np.std(obs_vals)), 
                      plot=axes[0])
        axes[0].get_lines()[0].set_markerfacecolor('red')
        axes[0].get_lines()[0].set_markeredgecolor('red')
        axes[0].get_lines()[0].set_alpha(0.7)
        axes[0].set_xlabel('Theoretical Quantiles (Obs Distribution)')
        axes[0].set_ylabel('Sample Quantiles (Raw Model)')
        axes[0].set_title('Q-Q Plot: Observations vs Raw Model')
        axes[0].grid(True, alpha=0.3)
        
        # QQ plot: Observations vs Debiased
        stats.probplot(debiased_vals, dist=stats.norm, sparams=(np.mean(obs_vals), np.std(obs_vals)), 
                      plot=axes[1])
        axes[1].get_lines()[0].set_markerfacecolor('green')
        axes[1].get_lines()[0].set_markeredgecolor('green')
        axes[1].get_lines()[0].set_alpha(0.7)
        axes[1].set_xlabel('Theoretical Quantiles (Obs Distribution)')
        axes[1].set_ylabel('Sample Quantiles (Debiased)')
        axes[1].set_title('Q-Q Plot: Observations vs Debiased')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'qq_plots.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_seasonal_cycle(self, data, variable='pr'):
        """
        Plot seasonal cycle (monthly means) before and after bias correction.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Calculate monthly means (spatial average)
        obs_monthly = data['obs'][variable].groupby('time.month').mean(dim=['time', 'x', 'y'])
        cm_hist_monthly = data['cm_hist'][variable].groupby('time.month').mean(dim=['time', 'x', 'y'])
        debiased_monthly = data['debiased'][variable].groupby('time.month').mean(dim=['time', 'x', 'y'])
        
        months = np.arange(1, 13)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Monthly means
        axes[0].plot(months, obs_monthly.values, 'o-', label='Observations', linewidth=2, markersize=6)
        axes[0].plot(months, cm_hist_monthly.values, 's-', label='Raw Model', linewidth=2, markersize=6)
        axes[0].plot(months, debiased_monthly.values, '^-', label='Debiased', linewidth=2, markersize=6)
        axes[0].set_xlabel('Month')
        axes[0].set_ylabel('Mean Precipitation (mm/day)')
        axes[0].set_title('Seasonal Cycle - Monthly Means')
        axes[0].set_xticks(months)
        axes[0].set_xticklabels(month_names)
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Bias (model - obs)
        cm_hist_bias = cm_hist_monthly.values - obs_monthly.values
        debiased_bias = debiased_monthly.values - obs_monthly.values
        
        axes[1].plot(months, cm_hist_bias, 's-', label='Raw Model Bias', linewidth=2, markersize=6, color='red')
        axes[1].plot(months, debiased_bias, '^-', label='Debiased Bias', linewidth=2, markersize=6, color='green')
        axes[1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[1].set_xlabel('Month')
        axes[1].set_ylabel('Bias (mm/day)')
        axes[1].set_title('Seasonal Bias (Model - Observations)')
        axes[1].set_xticks(months)
        axes[1].set_xticklabels(month_names)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'seasonal_cycle.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_wet_day_frequency(self, data, variable='pr', threshold=0.1):
        """
        Plot wet day frequency analysis.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        threshold : float
            Threshold for defining wet days (mm/day)
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Calculate wet day frequency (spatial and temporal average)
        obs_wet_freq = (data['obs'][variable] > threshold).mean().values * 100
        cm_hist_wet_freq = (data['cm_hist'][variable] > threshold).mean().values * 100
        debiased_wet_freq = (data['debiased'][variable] > threshold).mean().values * 100
        
        # Bar plot of wet day frequencies
        datasets = ['Observations', 'Raw Model', 'Debiased']
        frequencies = [obs_wet_freq, cm_hist_wet_freq, debiased_wet_freq]
        colors = ['blue', 'red', 'green']
        
        bars = axes[0].bar(datasets, frequencies, color=colors, alpha=0.7)
        axes[0].set_ylabel('Wet Day Frequency (%)')
        axes[0].set_title(f'Wet Day Frequency (>{threshold} mm/day)')
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, freq in zip(bars, frequencies):
            axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{freq:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Monthly wet day frequency
        obs_monthly_wet = (data['obs'][variable] > threshold).groupby('time.month').mean(dim=['time', 'x', 'y']) * 100
        cm_hist_monthly_wet = (data['cm_hist'][variable] > threshold).groupby('time.month').mean(dim=['time', 'x', 'y']) * 100
        debiased_monthly_wet = (data['debiased'][variable] > threshold).groupby('time.month').mean(dim=['time', 'x', 'y']) * 100
        
        months = np.arange(1, 13)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        axes[1].plot(months, obs_monthly_wet.values, 'o-', label='Observations', linewidth=2, markersize=6)
        axes[1].plot(months, cm_hist_monthly_wet.values, 's-', label='Raw Model', linewidth=2, markersize=6)
        axes[1].plot(months, debiased_monthly_wet.values, '^-', label='Debiased', linewidth=2, markersize=6)
        axes[1].set_xlabel('Month')
        axes[1].set_ylabel('Wet Day Frequency (%)')
        axes[1].set_title(f'Monthly Wet Day Frequency (>{threshold} mm/day)')
        axes[1].set_xticks(months)
        axes[1].set_xticklabels(month_names)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'wet_day_frequency.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_extreme_values(self, data, variable='pr', percentiles=[95, 99]):
        """
        Plot extreme value analysis (high percentiles).
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        percentiles : list
            List of percentiles to analyze
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Calculate percentiles (spatial and temporal)
        obs_percentiles = []
        cm_hist_percentiles = []
        debiased_percentiles = []
        
        for p in percentiles:
            obs_percentiles.append(np.percentile(data['obs'][variable].values, p))
            cm_hist_percentiles.append(np.percentile(data['cm_hist'][variable].values, p))
            debiased_percentiles.append(np.percentile(data['debiased'][variable].values, p))
        
        # Bar plot of extreme percentiles
        x = np.arange(len(percentiles))
        width = 0.25
        
        bars1 = axes[0].bar(x - width, obs_percentiles, width, label='Observations', alpha=0.7)
        bars2 = axes[0].bar(x, cm_hist_percentiles, width, label='Raw Model', alpha=0.7)
        bars3 = axes[0].bar(x + width, debiased_percentiles, width, label='Debiased', alpha=0.7)
        
        axes[0].set_xlabel('Percentile')
        axes[0].set_ylabel('Precipitation (mm/day)')
        axes[0].set_title('Extreme Value Comparison')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels([f'P{p}' for p in percentiles])
        axes[0].legend()
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                axes[0].text(bar.get_x() + bar.get_width()/2, height + 0.1,
                           f'{height:.1f}', ha='center', va='bottom', fontsize=9)
        
        # Extreme value bias
        cm_hist_bias = np.array(cm_hist_percentiles) - np.array(obs_percentiles)
        debiased_bias = np.array(debiased_percentiles) - np.array(obs_percentiles)
        
        bars1 = axes[1].bar(x - width/2, cm_hist_bias, width, label='Raw Model Bias', alpha=0.7, color='red')
        bars2 = axes[1].bar(x + width/2, debiased_bias, width, label='Debiased Bias', alpha=0.7, color='green')
        
        axes[1].axhline(y=0, color='black', linestyle='--', alpha=0.5)
        axes[1].set_xlabel('Percentile')
        axes[1].set_ylabel('Bias (mm/day)')
        axes[1].set_title('Extreme Value Bias (Model - Observations)')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels([f'P{p}' for p in percentiles])
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                axes[1].text(bar.get_x() + bar.get_width()/2, height + 0.05 if height >= 0 else height - 0.1,
                           f'{height:.1f}', ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'extreme_values.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_time_series(self, data, variable='pr', grid_point=(7, 7), n_days=365):
        """
        Plot sample time series for a representative point.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        grid_point : tuple
            Grid point coordinates (x, y)
        n_days : int
            Number of days to plot
        """
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        
        # Extract time series for the specified grid point
        x, y = grid_point
        obs_ts = data['obs'][variable].isel(x=x, y=y)[:n_days]
        cm_hist_ts = data['cm_hist'][variable].isel(x=x, y=y)[:n_days]
        debiased_ts = data['debiased'][variable].isel(x=x, y=y)[:n_days]
        
        time_vals = obs_ts.time.values
        
        # Full time series
        axes[0].plot(time_vals, obs_ts.values, label='Observations', linewidth=1, alpha=0.8)
        axes[0].plot(time_vals, cm_hist_ts.values, label='Raw Model', linewidth=1, alpha=0.8)
        axes[0].plot(time_vals, debiased_ts.values, label='Debiased', linewidth=1, alpha=0.8)
        axes[0].set_ylabel('Precipitation (mm/day)')
        axes[0].set_title(f'Time Series at Grid Point ({x}, {y}) - First {n_days} Days')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Format x-axis
        axes[0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)
        
        # Cumulative precipitation
        obs_cumsum = np.cumsum(obs_ts.values)
        cm_hist_cumsum = np.cumsum(cm_hist_ts.values)
        debiased_cumsum = np.cumsum(debiased_ts.values)
        
        axes[1].plot(time_vals, obs_cumsum, label='Observations', linewidth=2)
        axes[1].plot(time_vals, cm_hist_cumsum, label='Raw Model', linewidth=2)
        axes[1].plot(time_vals, debiased_cumsum, label='Debiased', linewidth=2)
        axes[1].set_xlabel('Time')
        axes[1].set_ylabel('Cumulative Precipitation (mm)')
        axes[1].set_title('Cumulative Precipitation')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Format x-axis
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'time_series.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def plot_scatter_plots(self, data, variable='pr', grid_point=(7, 7)):
        """
        Plot scatter plots with 1:1 line comparing observed vs model data.
        
        Parameters
        ----------
        data : dict
            Dictionary containing obs, cm_hist, and debiased datasets
        variable : str
            Variable name to plot
        grid_point : tuple
            Grid point coordinates (x, y)
        """
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Extract data for the specified grid point
        x, y = grid_point
        obs_vals = data['obs'][variable].isel(x=x, y=y).values
        cm_hist_vals = data['cm_hist'][variable].isel(x=x, y=y).values
        debiased_vals = data['debiased'][variable].isel(x=x, y=y).values
        
        # Observations vs Raw Model
        axes[0].scatter(obs_vals, cm_hist_vals, alpha=0.6, s=20, color='red', label='Data points')
        
        # 1:1 line
        max_val = max(np.max(obs_vals), np.max(cm_hist_vals))
        axes[0].plot([0, max_val], [0, max_val], 'k--', linewidth=2, label='1:1 line')
        
        # Calculate correlation
        corr_raw = np.corrcoef(obs_vals, cm_hist_vals)[0, 1]
        
        axes[0].set_xlabel('Observations (mm/day)')
        axes[0].set_ylabel('Raw Model (mm/day)')
        axes[0].set_title(f'Observations vs Raw Model\n(r = {corr_raw:.3f})')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        axes[0].set_xlim(0, max_val)
        axes[0].set_ylim(0, max_val)
        
        # Observations vs Debiased
        axes[1].scatter(obs_vals, debiased_vals, alpha=0.6, s=20, color='green', label='Data points')
        
        # 1:1 line
        max_val = max(np.max(obs_vals), np.max(debiased_vals))
        axes[1].plot([0, max_val], [0, max_val], 'k--', linewidth=2, label='1:1 line')
        
        # Calculate correlation
        corr_debiased = np.corrcoef(obs_vals, debiased_vals)[0, 1]
        
        axes[1].set_xlabel('Observations (mm/day)')
        axes[1].set_ylabel('Debiased (mm/day)')
        axes[1].set_title(f'Observations vs Debiased\n(r = {corr_debiased:.3f})')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        axes[1].set_xlim(0, max_val)
        axes[1].set_ylim(0, max_val)
        
        plt.tight_layout()
        
        # Save figure
        filename = self.output_dir / 'scatter_plots.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        self.figures_created.append(filename)
        plt.close()
        
        print(f"Created: {filename}")
    
    def create_figures_index(self):
        """Create a markdown index of all generated figures."""
        index_content = f"""# Bias Correction Diagnostic Figures

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This document provides an index of diagnostic figures generated for bias correction evaluation, 
following the ibicus framework and best practices.

## References

- **GitHub Repository**: [ecmwf-projects/ibicus](https://github.com/ecmwf-projects/ibicus)
- **Documentation**: [ibicus.readthedocs.io](https://ibicus.readthedocs.io/en/latest/)
- **Paper**: Spuler et al. 2024, Geoscientific Model Development, DOI: [10.5194/gmd-17-1249-2024](https://doi.org/10.5194/gmd-17-1249-2024)

## Diagnostic Figures

"""
        
        figure_descriptions = {
            'histograms_and_ecdfs.png': 'Distribution histograms and empirical cumulative distribution functions (ECDFs) comparing observations, raw model, and debiased data.',
            'qq_plots.png': 'Quantile-quantile plots assessing distributional alignment between observed and model data before and after bias correction.',
            'seasonal_cycle.png': 'Seasonal cycle analysis showing monthly means and bias patterns throughout the year.',
            'wet_day_frequency.png': 'Wet day frequency analysis examining the occurrence of precipitation events above threshold.',
            'extreme_values.png': 'Extreme value analysis comparing high percentiles (P95, P99) and their bias correction performance.',
            'time_series.png': 'Sample time series and cumulative precipitation at a representative grid point.',
            'scatter_plots.png': 'Scatter plots with 1:1 reference lines comparing observed vs raw and debiased data.'
        }
        
        for i, filename in enumerate(self.figures_created, 1):
            figure_name = filename.name
            description = figure_descriptions.get(figure_name, 'Diagnostic plot for bias correction evaluation.')
            
            index_content += f"""
### {i}. {figure_name.replace('_', ' ').replace('.png', '').title()}

**File**: `{figure_name}`

**Description**: {description}

![{figure_name}]({figure_name})

---
"""
        
        # Add summary
        index_content += f"""
## Summary

Total figures generated: {len(self.figures_created)}

These diagnostic plots provide comprehensive evaluation of bias correction performance across multiple dimensions:
- **Distributional properties**: Histograms, ECDFs, and Q-Q plots
- **Temporal patterns**: Seasonal cycles and time series analysis  
- **Extreme events**: High percentile analysis
- **Precipitation characteristics**: Wet day frequency and intensity
- **Overall performance**: Scatter plots and correlation analysis

The plots follow ibicus evaluation framework standards and can be used to:
1. Assess the effectiveness of bias correction methods
2. Identify remaining biases and areas for improvement
3. Compare different bias correction approaches
4. Validate model performance for impact studies

For detailed methodology and interpretation guidelines, refer to the ibicus documentation and Spuler et al. (2024) paper.
"""
        
        # Save index file
        index_file = self.output_dir / 'figures_index.md'
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        print(f"Created figures index: {index_file}")
        return index_file
    
    def generate_all_plots(self, obs_file=None, cm_hist_file=None, debiased_file=None, variable='pr'):
        """
        Generate all diagnostic plots.
        
        Parameters
        ----------
        obs_file : str, optional
            Path to observational data file
        cm_hist_file : str, optional
            Path to climate model historical data file
        debiased_file : str, optional
            Path to debiased data file
        variable : str
            Variable name to analyze
        """
        print("=== Bias Correction Diagnostic Plots ===")
        print(f"Output directory: {self.output_dir}")
        print()
        
        # Load data
        print("Loading data...")
        data = self.load_data(obs_file, cm_hist_file, debiased_file)
        print()
        
        # Generate all plots
        print("Generating diagnostic plots...")
        self.plot_histograms_and_ecdfs(data, variable)
        self.plot_qq_plots(data, variable)
        self.plot_seasonal_cycle(data, variable)
        self.plot_wet_day_frequency(data, variable)
        self.plot_extreme_values(data, variable)
        self.plot_time_series(data, variable)
        self.plot_scatter_plots(data, variable)
        
        # Create index
        print()
        print("Creating figures index...")
        self.create_figures_index()
        
        print()
        print(f"=== Complete! Generated {len(self.figures_created)} diagnostic plots ===")
        print(f"All figures saved to: {self.output_dir}")


def main():
    """Main function to run the diagnostic plotting."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate bias correction diagnostic plots')
    parser.add_argument('--obs', help='Path to observational data file')
    parser.add_argument('--cm-hist', help='Path to climate model historical data file')
    parser.add_argument('--debiased', help='Path to debiased data file')
    parser.add_argument('--variable', default='pr', help='Variable name (default: pr)')
    parser.add_argument('--output-dir', default='data/processed/ibicus/figures', 
                       help='Output directory for figures')
    
    args = parser.parse_args()
    
    # Create diagnostics instance
    diagnostics = BiasCorrectionDiagnostics(output_dir=args.output_dir)
    
    # Generate all plots
    diagnostics.generate_all_plots(
        obs_file=args.obs,
        cm_hist_file=args.cm_hist,
        debiased_file=args.debiased,
        variable=args.variable
    )


if __name__ == "__main__":
    main()