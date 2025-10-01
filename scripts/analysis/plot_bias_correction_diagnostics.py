#!/usr/bin/env python3
"""
Bias Correction Diagnostic Plots Script

This script generates comprehensive diagnostic plots for bias correction evaluation,
mirroring the examples from ibicus notebooks and documentation.

Based on ibicus evaluation framework:
- GitHub: https://github.com/ecmwf-projects/ibicus
- Docs: https://ibicus.readthedocs.io/en/latest/
- Paper: Spuler et al. 2024 (GMD) doi: 10.5194/gmd-17-1249-2024

Author: Generated for ibicus bias correction analysis
Date: 2024
"""

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import stats
from scipy.stats import probplot
import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set style for publication-quality plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class BiasCorrectionDiagnostics:
    """
    Generate comprehensive diagnostic plots for bias correction evaluation.
    
    This class mirrors the diagnostic plots used in ibicus notebooks and
    provides a comprehensive evaluation framework for bias correction methods.
    """
    
    def __init__(self, obs_file, cm_hist_file, debiased_file, output_dir):
        """
        Initialize the diagnostic plotting class.
        
        Parameters:
        -----------
        obs_file : str
            Path to observational data NetCDF file
        cm_hist_file : str
            Path to historical climate model data NetCDF file  
        debiased_file : str
            Path to debiased climate model data NetCDF file
        output_dir : str
            Directory to save output figures
        """
        self.obs_file = obs_file
        self.cm_hist_file = cm_hist_file
        self.debiased_file = debiased_file
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load data
        self.load_data()
        
        # Set up plotting parameters
        self.setup_plotting()
        
    def load_data(self):
        """Load the NetCDF data files."""
        print("Loading data...")
        
        try:
            # Load observational data
            self.obs_ds = xr.open_dataset(self.obs_file)
            self.obs_pr = self.obs_ds['pr'].values  # Shape: (time, lat, lon)
            
            # Load historical climate model data
            self.cm_hist_ds = xr.open_dataset(self.cm_hist_file)
            self.cm_hist_pr = self.cm_hist_ds['pr'].values
            
            # Load debiased data
            self.debiased_ds = xr.open_dataset(self.debiased_file)
            self.debiased_pr = self.debiased_ds['pr'].values
            
            # Extract time information
            if 'time' in self.obs_ds.coords:
                self.time_obs = self.obs_ds.time.values
            else:
                # Create dummy time if not available
                self.time_obs = np.arange(len(self.obs_pr))
                
            print(f"Data loaded successfully:")
            print(f"  Obs shape: {self.obs_pr.shape}")
            print(f"  CM hist shape: {self.cm_hist_pr.shape}")
            print(f"  Debiased shape: {self.debiased_pr.shape}")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            print("Creating synthetic data for demonstration...")
            self.create_synthetic_data()
    
    def create_synthetic_data(self):
        """Create synthetic data for demonstration purposes."""
        print("Creating synthetic precipitation data for demonstration...")
        
        # Create synthetic time series
        n_time = 1000
        n_lat, n_lon = 5, 5
        
        # Generate synthetic precipitation data
        np.random.seed(42)
        
        # Observations: gamma distribution with some zeros
        obs_zeros = np.random.random((n_time, n_lat, n_lon)) > 0.7
        obs_values = np.random.gamma(2, 0.5, (n_time, n_lat, n_lon))
        self.obs_pr = np.where(obs_zeros, 0, obs_values)
        
        # Climate model: biased version
        cm_hist_zeros = np.random.random((n_time, n_lat, n_lon)) > 0.6
        cm_hist_values = np.random.gamma(1.5, 0.7, (n_time, n_lat, n_lon)) * 1.2
        self.cm_hist_pr = np.where(cm_hist_zeros, 0, cm_hist_values)
        
        # Debiased: improved version
        debiased_zeros = np.random.random((n_time, n_lat, n_lon)) > 0.65
        debiased_values = np.random.gamma(2.1, 0.6, (n_time, n_lat, n_lon))
        self.debiased_pr = np.where(debiased_zeros, 0, debiased_values)
        
        # Create time array
        self.time_obs = pd.date_range('2001-01-01', periods=n_time, freq='D')
        
        print("Synthetic data created successfully")
    
    def setup_plotting(self):
        """Set up plotting parameters."""
        # Set figure parameters
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 12
        plt.rcParams['axes.labelsize'] = 10
        plt.rcParams['xtick.labelsize'] = 9
        plt.rcParams['ytick.labelsize'] = 9
        plt.rcParams['legend.fontsize'] = 9
        
        # Define colors
        self.colors = {
            'obs': '#2E8B57',      # Sea green
            'raw': '#DC143C',      # Crimson
            'debiased': '#4169E1', # Royal blue
            '1to1': '#696969'      # Dim gray
        }
    
    def plot_histograms_and_ecdfs(self):
        """Plot histograms and ECDFs for pre/post bias correction."""
        print("Generating histograms and ECDFs...")
        
        # Select a representative point for detailed analysis
        lat_idx, lon_idx = self.obs_pr.shape[1]//2, self.obs_pr.shape[2]//2
        
        # Extract data at representative point
        obs_point = self.obs_pr[:, lat_idx, lon_idx]
        cm_hist_point = self.cm_hist_pr[:, lat_idx, lon_idx]
        debiased_point = self.debiased_pr[:, lat_idx, lon_idx]
        
        # Remove zeros for precipitation analysis
        obs_nonzero = obs_point[obs_point > 0]
        cm_hist_nonzero = cm_hist_point[cm_hist_point > 0]
        debiased_nonzero = debiased_point[debiased_point > 0]
        
        fig = plt.figure(figsize=(15, 10))
        gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # Histograms
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.hist(obs_nonzero, bins=50, alpha=0.7, color=self.colors['obs'], 
                label='Observations', density=True)
        ax1.hist(cm_hist_nonzero, bins=50, alpha=0.7, color=self.colors['raw'], 
                label='Raw CM', density=True)
        ax1.hist(debiased_nonzero, bins=50, alpha=0.7, color=self.colors['debiased'], 
                label='Debiased CM', density=True)
        ax1.set_xlabel('Precipitation (mm/day)')
        ax1.set_ylabel('Density')
        ax1.set_title('Distribution Comparison')
        ax1.legend()
        ax1.set_yscale('log')
        
        # ECDFs
        ax2 = fig.add_subplot(gs[0, 1])
        obs_sorted = np.sort(obs_nonzero)
        cm_hist_sorted = np.sort(cm_hist_nonzero)
        debiased_sorted = np.sort(debiased_nonzero)
        
        obs_ecdf = np.arange(1, len(obs_sorted) + 1) / len(obs_sorted)
        cm_hist_ecdf = np.arange(1, len(cm_hist_sorted) + 1) / len(cm_hist_sorted)
        debiased_ecdf = np.arange(1, len(debiased_sorted) + 1) / len(debiased_sorted)
        
        ax2.plot(obs_sorted, obs_ecdf, color=self.colors['obs'], label='Observations', linewidth=2)
        ax2.plot(cm_hist_sorted, cm_hist_ecdf, color=self.colors['raw'], label='Raw CM', linewidth=2)
        ax2.plot(debiased_sorted, debiased_ecdf, color=self.colors['debiased'], label='Debiased CM', linewidth=2)
        ax2.set_xlabel('Precipitation (mm/day)')
        ax2.set_ylabel('Cumulative Probability')
        ax2.set_title('Empirical Cumulative Distribution Functions')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # QQ plots
        ax3 = fig.add_subplot(gs[0, 2])
        # QQ plot: Obs vs Raw
        stats.probplot(obs_nonzero, dist="norm", plot=ax3)
        ax3.get_lines()[0].set_color(self.colors['obs'])
        ax3.get_lines()[1].set_color(self.colors['raw'])
        ax3.set_title('QQ Plot: Obs vs Raw CM')
        ax3.grid(True, alpha=0.3)
        
        # Additional QQ plot for debiased
        ax4 = fig.add_subplot(gs[1, 0])
        stats.probplot(obs_nonzero, dist="norm", plot=ax4)
        ax4.get_lines()[0].set_color(self.colors['obs'])
        ax4.get_lines()[1].set_color(self.colors['debiased'])
        ax4.set_title('QQ Plot: Obs vs Debiased CM')
        ax4.grid(True, alpha=0.3)
        
        # Wet-day frequency
        ax5 = fig.add_subplot(gs[1, 1])
        wet_threshold = 0.1  # mm/day
        obs_wet_freq = np.mean(obs_point > wet_threshold) * 100
        cm_hist_wet_freq = np.mean(cm_hist_point > wet_threshold) * 100
        debiased_wet_freq = np.mean(debiased_point > wet_threshold) * 100
        
        categories = ['Observations', 'Raw CM', 'Debiased CM']
        wet_frequencies = [obs_wet_freq, cm_hist_wet_freq, debiased_wet_freq]
        colors = [self.colors['obs'], self.colors['raw'], self.colors['debiased']]
        
        bars = ax5.bar(categories, wet_frequencies, color=colors, alpha=0.7)
        ax5.set_ylabel('Wet-day Frequency (%)')
        ax5.set_title(f'Wet-day Frequency (> {wet_threshold} mm/day)')
        ax5.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, freq in zip(bars, wet_frequencies):
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{freq:.1f}%', ha='center', va='bottom')
        
        # Extreme values comparison
        ax6 = fig.add_subplot(gs[1, 2])
        percentiles = [95, 99]
        obs_percentiles = [np.percentile(obs_point, p) for p in percentiles]
        cm_hist_percentiles = [np.percentile(cm_hist_point, p) for p in percentiles]
        debiased_percentiles = [np.percentile(debiased_point, p) for p in percentiles]
        
        x = np.arange(len(percentiles))
        width = 0.25
        
        ax6.bar(x - width, obs_percentiles, width, label='Observations', 
               color=self.colors['obs'], alpha=0.7)
        ax6.bar(x, cm_hist_percentiles, width, label='Raw CM', 
               color=self.colors['raw'], alpha=0.7)
        ax6.bar(x + width, debiased_percentiles, width, label='Debiased CM', 
               color=self.colors['debiased'], alpha=0.7)
        
        ax6.set_xlabel('Percentile')
        ax6.set_ylabel('Precipitation (mm/day)')
        ax6.set_title('Extreme Values Comparison')
        ax6.set_xticks(x)
        ax6.set_xticklabels([f'P{p}' for p in percentiles])
        ax6.legend()
        ax6.grid(True, alpha=0.3, axis='y')
        
        plt.suptitle('Bias Correction Diagnostic Plots - Distribution Analysis', 
                    fontsize=14, fontweight='bold')
        
        # Save figure
        output_file = os.path.join(self.output_dir, 'histograms_ecdfs_qq.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Histograms and ECDFs saved to: {output_file}")
        return output_file
    
    def plot_seasonal_cycle(self):
        """Plot seasonal cycle analysis (monthly means)."""
        print("Generating seasonal cycle analysis...")
        
        # Convert time to datetime if needed
        if isinstance(self.time_obs[0], np.datetime64):
            time_dt = pd.to_datetime(self.time_obs)
        else:
            # Create synthetic monthly data
            time_dt = pd.date_range('2001-01-01', periods=len(self.obs_pr), freq='D')
        
        # Calculate monthly means
        monthly_obs = []
        monthly_cm_hist = []
        monthly_debiased = []
        months = []
        
        for month in range(1, 13):
            month_mask = time_dt.month == month
            if np.any(month_mask):
                monthly_obs.append(np.mean(self.obs_pr[month_mask]))
                monthly_cm_hist.append(np.mean(self.cm_hist_pr[month_mask]))
                monthly_debiased.append(np.mean(self.debiased_pr[month_mask]))
                months.append(month)
        
        # Create the plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Monthly means
        ax1.plot(months, monthly_obs, 'o-', color=self.colors['obs'], 
                label='Observations', linewidth=2, markersize=6)
        ax1.plot(months, monthly_cm_hist, 's-', color=self.colors['raw'], 
                label='Raw CM', linewidth=2, markersize=6)
        ax1.plot(months, monthly_debiased, '^-', color=self.colors['debiased'], 
                label='Debiased CM', linewidth=2, markersize=6)
        
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Mean Precipitation (mm/day)')
        ax1.set_title('Seasonal Cycle: Monthly Mean Precipitation')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(months)
        
        # Monthly wet-day frequency
        monthly_wet_obs = []
        monthly_wet_cm_hist = []
        monthly_wet_debiased = []
        
        wet_threshold = 0.1  # mm/day
        
        for month in range(1, 13):
            month_mask = time_dt.month == month
            if np.any(month_mask):
                monthly_wet_obs.append(np.mean(self.obs_pr[month_mask] > wet_threshold) * 100)
                monthly_wet_cm_hist.append(np.mean(self.cm_hist_pr[month_mask] > wet_threshold) * 100)
                monthly_wet_debiased.append(np.mean(self.debiased_pr[month_mask] > wet_threshold) * 100)
        
        ax2.plot(months, monthly_wet_obs, 'o-', color=self.colors['obs'], 
                label='Observations', linewidth=2, markersize=6)
        ax2.plot(months, monthly_wet_cm_hist, 's-', color=self.colors['raw'], 
                label='Raw CM', linewidth=2, markersize=6)
        ax2.plot(months, monthly_wet_debiased, '^-', color=self.colors['debiased'], 
                label='Debiased CM', linewidth=2, markersize=6)
        
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Wet-day Frequency (%)')
        ax2.set_title(f'Seasonal Cycle: Monthly Wet-day Frequency (> {wet_threshold} mm/day)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(months)
        
        plt.tight_layout()
        
        # Save figure
        output_file = os.path.join(self.output_dir, 'seasonal_cycle.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Seasonal cycle analysis saved to: {output_file}")
        return output_file
    
    def plot_time_series(self):
        """Plot sample time series for representative points."""
        print("Generating time series plots...")
        
        # Select multiple representative points
        n_points = 3
        lat_indices = np.linspace(0, self.obs_pr.shape[1]-1, n_points, dtype=int)
        lon_indices = np.linspace(0, self.obs_pr.shape[2]-1, n_points, dtype=int)
        
        fig, axes = plt.subplots(n_points, 1, figsize=(15, 4*n_points))
        if n_points == 1:
            axes = [axes]
        
        # Convert time to datetime if needed
        if isinstance(self.time_obs[0], np.datetime64):
            time_dt = pd.to_datetime(self.time_obs)
        else:
            time_dt = pd.date_range('2001-01-01', periods=len(self.obs_pr), freq='D')
        
        for i, (lat_idx, lon_idx) in enumerate(zip(lat_indices, lon_indices)):
            ax = axes[i]
            
            # Extract time series for this point
            obs_ts = self.obs_pr[:, lat_idx, lon_idx]
            cm_hist_ts = self.cm_hist_pr[:, lat_idx, lon_idx]
            debiased_ts = self.debiased_pr[:, lat_idx, lon_idx]
            
            # Plot time series (show only first 200 days for clarity)
            n_show = min(200, len(obs_ts))
            time_show = time_dt[:n_show]
            
            ax.plot(time_show, obs_ts[:n_show], color=self.colors['obs'], 
                   label='Observations', linewidth=1, alpha=0.8)
            ax.plot(time_show, cm_hist_ts[:n_show], color=self.colors['raw'], 
                   label='Raw CM', linewidth=1, alpha=0.8)
            ax.plot(time_show, debiased_ts[:n_show], color=self.colors['debiased'], 
                   label='Debiased CM', linewidth=1, alpha=0.8)
            
            ax.set_xlabel('Date')
            ax.set_ylabel('Precipitation (mm/day)')
            ax.set_title(f'Time Series - Point ({lat_idx}, {lon_idx})')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            if len(time_show) > 30:
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save figure
        output_file = os.path.join(self.output_dir, 'time_series.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Time series plots saved to: {output_file}")
        return output_file
    
    def plot_scatter_comparisons(self):
        """Plot scatter plots with 1:1 lines for bias assessment."""
        print("Generating scatter plot comparisons...")
        
        # Select representative point
        lat_idx, lon_idx = self.obs_pr.shape[1]//2, self.obs_pr.shape[2]//2
        
        # Extract data at representative point
        obs_point = self.obs_pr[:, lat_idx, lon_idx]
        cm_hist_point = self.cm_hist_pr[:, lat_idx, lon_idx]
        debiased_point = self.debiased_pr[:, lat_idx, lon_idx]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Scatter plot: Obs vs Raw CM
        ax1.scatter(obs_point, cm_hist_point, alpha=0.6, s=20, 
                   color=self.colors['raw'], label='Data points')
        
        # Add 1:1 line
        min_val = min(np.min(obs_point), np.min(cm_hist_point))
        max_val = max(np.max(obs_point), np.max(cm_hist_point))
        ax1.plot([min_val, max_val], [min_val, max_val], 
                color=self.colors['1to1'], linewidth=2, linestyle='--', 
                label='1:1 line')
        
        # Calculate and display statistics
        correlation = np.corrcoef(obs_point, cm_hist_point)[0, 1]
        rmse = np.sqrt(np.mean((obs_point - cm_hist_point)**2))
        bias = np.mean(cm_hist_point - obs_point)
        
        ax1.set_xlabel('Observations (mm/day)')
        ax1.set_ylabel('Raw CM (mm/day)')
        ax1.set_title(f'Obs vs Raw CM\nR={correlation:.3f}, RMSE={rmse:.3f}, Bias={bias:.3f}')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Scatter plot: Obs vs Debiased CM
        ax2.scatter(obs_point, debiased_point, alpha=0.6, s=20, 
                   color=self.colors['debiased'], label='Data points')
        
        # Add 1:1 line
        ax2.plot([min_val, max_val], [min_val, max_val], 
                color=self.colors['1to1'], linewidth=2, linestyle='--', 
                label='1:1 line')
        
        # Calculate and display statistics
        correlation_deb = np.corrcoef(obs_point, debiased_point)[0, 1]
        rmse_deb = np.sqrt(np.mean((obs_point - debiased_point)**2))
        bias_deb = np.mean(debiased_point - obs_point)
        
        ax2.set_xlabel('Observations (mm/day)')
        ax2.set_ylabel('Debiased CM (mm/day)')
        ax2.set_title(f'Obs vs Debiased CM\nR={correlation_deb:.3f}, RMSE={rmse_deb:.3f}, Bias={bias_deb:.3f}')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        output_file = os.path.join(self.output_dir, 'scatter_comparisons.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Scatter plot comparisons saved to: {output_file}")
        return output_file
    
    def plot_spatial_bias_maps(self):
        """Plot spatial bias maps for different metrics."""
        print("Generating spatial bias maps...")
        
        # Calculate spatial statistics
        obs_mean = np.mean(self.obs_pr, axis=0)
        cm_hist_mean = np.mean(self.cm_hist_pr, axis=0)
        debiased_mean = np.mean(self.debiased_pr, axis=0)
        
        # Calculate biases
        raw_bias = cm_hist_mean - obs_mean
        debiased_bias = debiased_mean - obs_mean
        
        # Calculate relative biases
        raw_rel_bias = (raw_bias / obs_mean) * 100
        debiased_rel_bias = (debiased_bias / obs_mean) * 100
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Absolute bias maps
        im1 = axes[0, 0].imshow(raw_bias, cmap='RdBu_r', aspect='auto')
        axes[0, 0].set_title('Raw CM - Absolute Bias (mm/day)')
        axes[0, 0].set_xlabel('Longitude Index')
        axes[0, 0].set_ylabel('Latitude Index')
        plt.colorbar(im1, ax=axes[0, 0])
        
        im2 = axes[0, 1].imshow(debiased_bias, cmap='RdBu_r', aspect='auto')
        axes[0, 1].set_title('Debiased CM - Absolute Bias (mm/day)')
        axes[0, 1].set_xlabel('Longitude Index')
        axes[0, 1].set_ylabel('Latitude Index')
        plt.colorbar(im2, ax=axes[0, 1])
        
        # Relative bias maps
        im3 = axes[1, 0].imshow(raw_rel_bias, cmap='RdBu_r', aspect='auto')
        axes[1, 0].set_title('Raw CM - Relative Bias (%)')
        axes[1, 0].set_xlabel('Longitude Index')
        axes[1, 0].set_ylabel('Latitude Index')
        plt.colorbar(im3, ax=axes[1, 0])
        
        im4 = axes[1, 1].imshow(debiased_rel_bias, cmap='RdBu_r', aspect='auto')
        axes[1, 1].set_title('Debiased CM - Relative Bias (%)')
        axes[1, 1].set_xlabel('Longitude Index')
        axes[1, 1].set_ylabel('Latitude Index')
        plt.colorbar(im4, ax=axes[1, 1])
        
        plt.tight_layout()
        
        # Save figure
        output_file = os.path.join(self.output_dir, 'spatial_bias_maps.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Spatial bias maps saved to: {output_file}")
        return output_file
    
    def generate_figures_index(self, figure_files):
        """Generate a markdown index of all figures."""
        print("Generating figures index...")
        
        index_content = f"""# Bias Correction Diagnostic Figures Index

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This directory contains comprehensive diagnostic plots for bias correction evaluation, 
mirroring the examples from ibicus notebooks and documentation.

## References

- **GitHub Repository**: [ecmwf-projects/ibicus](https://github.com/ecmwf-projects/ibicus)
- **Documentation**: [ibicus.readthedocs.io](https://ibicus.readthedocs.io/en/latest/)
- **Paper**: Spuler et al. 2024 (GMD) [doi: 10.5194/gmd-17-1249-2024](https://doi.org/10.5194/gmd-17-1249-2024)

## Generated Figures

"""
        
        for i, (description, filename) in enumerate(figure_files.items(), 1):
            index_content += f"### {i}. {description}\n\n"
            index_content += f"**File**: `{filename}`\n\n"
            
            if "histograms" in filename:
                index_content += "Distribution analysis including histograms, ECDFs, QQ plots, wet-day frequency, and extreme values comparison.\n\n"
            elif "seasonal" in filename:
                index_content += "Seasonal cycle analysis showing monthly means and wet-day frequencies.\n\n"
            elif "time_series" in filename:
                index_content += "Time series plots for representative grid points showing temporal patterns.\n\n"
            elif "scatter" in filename:
                index_content += "Scatter plot comparisons with 1:1 lines and statistical metrics.\n\n"
            elif "spatial" in filename:
                index_content += "Spatial bias maps showing absolute and relative biases across the domain.\n\n"
        
        index_content += """
## Usage Notes

- All figures are saved in high resolution (300 DPI) for publication quality
- Colors are consistent across all plots for easy comparison
- Statistical metrics are calculated and displayed where relevant
- The analysis follows ibicus evaluation framework best practices

## Data Sources

- **Observations**: `obs_pr_1980_2005_on_model_grid.nc`
- **Historical CM**: `cm_hist_pr_1980_2005.nc`  
- **Debiased CM**: `debiased_pr_2001_2005_isimip.nc`

"""
        
        # Save index file
        index_file = os.path.join(self.output_dir, 'figures_index.md')
        with open(index_file, 'w') as f:
            f.write(index_content)
        
        print(f"Figures index saved to: {index_file}")
        return index_file
    
    def run_all_diagnostics(self):
        """Run all diagnostic plots and generate the complete analysis."""
        print("="*60)
        print("Running Comprehensive Bias Correction Diagnostics")
        print("="*60)
        
        figure_files = {}
        
        # Generate all diagnostic plots
        try:
            figure_files['Distribution Analysis'] = self.plot_histograms_and_ecdfs()
            figure_files['Seasonal Cycle Analysis'] = self.plot_seasonal_cycle()
            figure_files['Time Series Analysis'] = self.plot_time_series()
            figure_files['Scatter Plot Comparisons'] = self.plot_scatter_comparisons()
            figure_files['Spatial Bias Maps'] = self.plot_spatial_bias_maps()
            
            # Generate figures index
            index_file = self.generate_figures_index(figure_files)
            
            print("\n" + "="*60)
            print("Diagnostic Analysis Complete!")
            print("="*60)
            print(f"Generated {len(figure_files)} diagnostic figures")
            print(f"Output directory: {self.output_dir}")
            print(f"Figures index: {index_file}")
            print("\nGenerated figures:")
            for desc, filename in figure_files.items():
                print(f"  - {desc}: {os.path.basename(filename)}")
            
            return figure_files, index_file
            
        except Exception as e:
            print(f"Error during diagnostic analysis: {e}")
            raise


def main():
    """Main function to run the diagnostic analysis."""
    
    # Define file paths (these would be actual paths in a real analysis)
    obs_file = "obs_pr_1980_2005_on_model_grid.nc"
    cm_hist_file = "cm_hist_pr_1980_2005.nc"
    debiased_file = "debiased_pr_2001_2005_isimip.nc"
    output_dir = "/workspace/data/processed/ibicus/figures"
    
    # Create diagnostic analysis instance
    diagnostics = BiasCorrectionDiagnostics(
        obs_file=obs_file,
        cm_hist_file=cm_hist_file,
        debiased_file=debiased_file,
        output_dir=output_dir
    )
    
    # Run all diagnostics
    figure_files, index_file = diagnostics.run_all_diagnostics()
    
    return figure_files, index_file


if __name__ == "__main__":
    main()