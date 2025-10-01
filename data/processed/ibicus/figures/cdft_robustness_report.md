# CDFt Robustness Investigation Report

Generated on: 2025-10-01

## Overview

This report investigates the "Quantiles must be in the range [0, 1]" error commonly encountered with the CDFt bias correction method and provides robust configuration recommendations based on analysis of the ibicus implementation.

## Background

The CDFt (CDF-transform) method uses empirical cumulative distribution functions (ECDFs) and their inverses (ICDFs) for quantile mapping. Issues can arise when:

1. **ECDF values reach exactly 0 or 1**: This can cause problems with inverse CDF calculations
2. **Extreme values outside training range**: Values beyond the observed range can cause extrapolation issues  
3. **Running window complications**: Running windows can introduce edge effects
4. **Stochastic Singularity Removal (SSR)**: Can interact poorly with sparse precipitation data
5. **Monthly application edge cases**: Month-specific fitting can fail with insufficient data

## Root Cause Analysis

Based on examination of the ibicus CDFt implementation (`/workspace/ibicus/debias/_cdft.py`), the quantile error typically occurs in these scenarios:

### 1. ECDF Boundary Issues
- When `ecdf()` returns values exactly 0.0 or 1.0
- These boundary values cause problems in `iecdf()` inverse calculations
- The `threshold_cdf_vals()` utility function in ibicus helps but may not always be applied

### 2. Running Window Edge Effects
- Running windows can create edge cases with insufficient data
- Window boundaries may not have enough samples for robust ECDF estimation
- Default window length (17 years) and step (9 years) may be too aggressive

### 3. SSR Complications
- Stochastic Singularity Removal replaces zeros with small random values
- This can create artificial quantiles that don't map well
- Particularly problematic with very sparse precipitation data

### 4. Monthly Application Issues
- Some months may have insufficient wet days for robust ECDF fitting
- Seasonal patterns can create months with extreme skewness
- Default monthly approach may fail in arid regions

## Recommended Robust Configurations

### Configuration 1: Conservative (Recommended)

```python
from ibicus.debias import CDFt

debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.ecdf_method = "linear_interpolation"  
debiaser.iecdf_method = "linear"
debiaser.SSR = False  # Disable for problematic data
debiaser.apply_by_month = True
```

**Rationale**: 
- Disables running windows to avoid edge effects
- Uses linear interpolation for smoother ECDF behavior
- Linear IECDF method handles boundary cases better
- Keeps monthly application for seasonality but disables SSR

### Configuration 2: Minimal Complexity

```python
debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.apply_by_month = False
debiaser.SSR = False
debiaser.ecdf_method = "step_function"
debiaser.iecdf_method = "inverted_cdf"
```

**Rationale**:
- Simplest possible configuration
- No seasonal or running window complications
- Uses default ECDF/IECDF methods but with safety features disabled

### Configuration 3: Robust with Clipping

```python
debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.ecdf_method = "linear_interpolation"
debiaser.iecdf_method = "nearest"  # Most robust for edge cases
debiaser.apply_by_month = True

# Manual clipping approach (if accessible)
# Clip ECDF probabilities to [1e-6, 1-1e-6] range
```

**Rationale**:
- Uses nearest neighbor IECDF to avoid interpolation issues
- Linear interpolation ECDF for smoothness
- Manual probability clipping prevents exact 0/1 values

## Implementation Strategy

### Step 1: Try Conservative Configuration First

```python
try:
    debiaser = CDFt.from_variable("pr")
    debiaser.running_window_mode = False
    debiaser.ecdf_method = "linear_interpolation"
    debiaser.iecdf_method = "linear"
    debiaser.SSR = False
    
    result = debiaser.apply(obs, cm_hist, cm_future)
    print("✅ CDFt successful with conservative settings")
    
except Exception as e:
    print(f"❌ Conservative CDFt failed: {e}")
    # Try minimal configuration
```

### Step 2: Fallback to Minimal Configuration

```python
try:
    debiaser = CDFt.from_variable("pr")
    debiaser.running_window_mode = False
    debiaser.apply_by_month = False
    debiaser.SSR = False
    
    result = debiaser.apply(obs, cm_hist, cm_future)
    print("✅ CDFt successful with minimal settings")
    
except Exception as e:
    print(f"❌ Minimal CDFt failed: {e}")
    # Consider alternative method (ISIMIP)
```

### Step 3: Alternative Method (ISIMIP)

```python
from ibicus.debias import ISIMIP

print("🔄 Falling back to ISIMIP method")
debiaser = ISIMIP.from_variable("pr")
result = debiaser.apply(obs, cm_hist, cm_future, 
                       time_obs=time_obs, 
                       time_cm_hist=time_cm_hist, 
                       time_cm_future=time_cm_future)
print("✅ ISIMIP successful")
```

## Data Preprocessing Recommendations

Before applying CDFt, consider these preprocessing steps:

### 1. Outlier Detection and Handling
```python
# Remove extreme outliers (>99.9th percentile)
p999 = np.percentile(obs[obs > 0], 99.9)
obs = np.clip(obs, 0, p999)
cm_hist = np.clip(cm_hist, 0, p999 * 2)  # Allow some model bias
cm_future = np.clip(cm_future, 0, p999 * 2)
```

### 2. Data Quality Checks
```python
# Check for sufficient wet days
wet_day_freq = np.mean(obs > 0.1)
if wet_day_freq < 0.1:  # Less than 10% wet days
    print("⚠️  Warning: Very sparse precipitation data")
    # Consider disabling SSR and monthly application
```

### 3. Monthly Data Sufficiency
```python
# Check monthly wet day counts
for month in range(1, 13):
    month_mask = time_month == month
    monthly_wet_days = np.sum((obs[month_mask] > 0.1))
    if monthly_wet_days < 10:
        print(f"⚠️  Warning: Month {month} has only {monthly_wet_days} wet days")
        # Consider apply_by_month = False
```

## Validation Checklist

After successful CDFt application, validate results:

### 1. Basic Checks
- [ ] No NaN values in output
- [ ] No infinite values in output  
- [ ] No negative precipitation values
- [ ] Output range is physically reasonable

### 2. Statistical Validation
- [ ] Mean bias significantly reduced
- [ ] Extreme percentiles (P95, P99) reasonable
- [ ] Wet day frequency preserved approximately
- [ ] Temporal correlation maintained

### 3. Diagnostic Plots
- [ ] Q-Q plots show improved alignment
- [ ] ECDFs converge between obs and corrected data
- [ ] Seasonal cycle preserved
- [ ] No artificial discontinuities

## Alternative Methods

If CDFt continues to fail despite robust configurations:

### 1. ISIMIP (Recommended Alternative)
- More robust to edge cases
- Trend-preserving by design
- Better handling of extreme values
- Proven track record in ISIMIP protocol

### 2. Quantile Mapping
- Simpler non-parametric approach
- Less prone to quantile range errors
- Good for basic bias correction needs

### 3. Quantile Delta Mapping
- Trend-preserving alternative
- Handles relative changes well
- More complex but often more robust

## Conclusion

The "Quantiles must be in the range [0, 1]" error in CDFt can be resolved through:

1. **Simplified configurations** that avoid problematic features
2. **Robust ECDF/IECDF method selection** 
3. **Proper data preprocessing** to handle edge cases
4. **Fallback to alternative methods** when CDFt fails

The recommended conservative configuration should resolve most issues while maintaining reasonable bias correction performance. For critical applications, ISIMIP provides a more robust alternative with similar trend-preserving properties.

## References

- **ibicus CDFt implementation**: `/workspace/ibicus/debias/_cdft.py`
- **Utility functions**: `/workspace/ibicus/utils/_math_utils.py`
- **Vrac et al. (2016)**: Original CDFt methodology with SSR
- **Famien et al. (2018)**: Monthly application approach
- **ISIMIP protocol**: Robust alternative bias correction framework

---

*This investigation was conducted based on analysis of the ibicus CDFt implementation and common failure modes reported in bias correction applications.*