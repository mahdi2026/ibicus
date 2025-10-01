# Bias Correction Diagnostic Figures Index

Generated on: 2024-12-19 15:30:00

This directory contains comprehensive diagnostic plots for bias correction evaluation, 
mirroring the examples from ibicus notebooks and documentation.

## References

- **GitHub Repository**: [ecmwf-projects/ibicus](https://github.com/ecmwf-projects/ibicus)
- **Documentation**: [ibicus.readthedocs.io](https://ibicus.readthedocs.io/en/latest/)
- **Paper**: Spuler et al. 2024 (GMD) [doi: 10.5194/gmd-17-1249-2024](https://doi.org/10.5194/gmd-17-1249-2024)

## Generated Figures

### 1. Distribution Analysis

**File**: `histograms_ecdfs_qq.png`

Distribution analysis including histograms, ECDFs, QQ plots, wet-day frequency, and extreme values comparison.

### 2. Seasonal Cycle Analysis

**File**: `seasonal_cycle.png`

Seasonal cycle analysis showing monthly means and wet-day frequencies.

### 3. Time Series Analysis

**File**: `time_series.png`

Time series plots for representative grid points showing temporal patterns.

### 4. Scatter Plot Comparisons

**File**: `scatter_comparisons.png`

Scatter plot comparisons with 1:1 lines and statistical metrics.

### 5. Spatial Bias Maps

**File**: `spatial_bias_maps.png`

Spatial bias maps showing absolute and relative biases across the domain.

## Usage Notes

- All figures are saved in high resolution (300 DPI) for publication quality
- Colors are consistent across all plots for easy comparison
- Statistical metrics are calculated and displayed where relevant
- The analysis follows ibicus evaluation framework best practices

## Data Sources

- **Observations**: `obs_pr_1980_2005_on_model_grid.nc`
- **Historical CM**: `cm_hist_pr_1980_2005.nc`  
- **Debiased CM**: `debiased_pr_2001_2005_isimip.nc`

## Key Diagnostic Plots from ibicus Examples

Based on analysis of ibicus notebooks, the following diagnostic plots are essential for bias correction evaluation:

1. **Empirical Cumulative Distribution Functions (ECDFs)**: Compare cumulative distributions of observed vs model data
2. **Quantile-Quantile (QQ) Plots**: Assess quantile alignment between datasets
3. **Distribution Histograms**: Visualize frequency distributions before/after bias correction
4. **Seasonal Cycle Analysis**: Monthly mean comparisons to assess seasonal pattern preservation
5. **Wet-Day Frequency Analysis**: Frequency of days exceeding precipitation thresholds
6. **Extreme Value Analysis**: 95th and 99th percentile comparisons
7. **Time Series Plots**: Temporal patterns at representative locations
8. **Scatter Plots with 1:1 Lines**: Statistical correlation and bias assessment
9. **Spatial Bias Maps**: Geographic distribution of biases
10. **Threshold Metrics**: ETCCDI climate indices and custom thresholds

## Implementation Notes

The diagnostic plots are generated using the same methodology as demonstrated in ibicus notebooks:
- **Notebook 01 Getting Started**: Basic bias correction workflow
- **Notebook 03 Evaluation**: Comprehensive evaluation framework
- **Notebook 05 ISIMIP Consistency**: Method validation and comparison

All plots follow ibicus best practices for bias correction evaluation and can be used for publication-quality analysis.