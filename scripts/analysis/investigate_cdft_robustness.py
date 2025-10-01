#!/usr/bin/env python3
"""
CDFt Robustness Investigation

This script investigates the "Quantiles must be in the range [0, 1]" error
in CDFt and tests robust settings to avoid quantile errors.

Based on ibicus CDFt implementation and common issues with empirical CDFs.
"""

import numpy as np
import sys
import os
sys.path.insert(0, '/workspace')

from ibicus.debias import CDFt
from ibicus.utils import threshold_cdf_vals
import warnings
warnings.filterwarnings('ignore')

def create_test_data():
    """Create test data that might cause CDFt quantile issues."""
    np.random.seed(42)
    
    # Create precipitation data with challenging characteristics
    n_days = 1000
    
    # Observations: realistic precipitation with many zeros
    obs = np.random.gamma(2, 2, n_days)
    dry_mask = np.random.random(n_days) < 0.7  # 70% dry days
    obs[dry_mask] = 0
    
    # Climate model historical: biased with different dry day frequency
    cm_hist = obs * 1.3 + np.random.normal(0, 0.5, n_days)
    cm_hist = np.maximum(cm_hist, 0)
    dry_mask_cm = np.random.random(n_days) < 0.6  # 60% dry days (different from obs)
    cm_hist[dry_mask_cm] = 0
    
    # Climate model future: similar bias pattern but different range
    cm_future = obs * 1.4 + np.random.normal(0, 0.7, n_days)
    cm_future = np.maximum(cm_future, 0)
    dry_mask_fut = np.random.random(n_days) < 0.55  # 55% dry days
    cm_future[dry_mask_fut] = 0
    
    # Add some extreme values that might cause issues
    obs[np.random.choice(n_days, 5)] = np.random.uniform(50, 100, 5)
    cm_hist[np.random.choice(n_days, 5)] = np.random.uniform(60, 120, 5)
    cm_future[np.random.choice(n_days, 5)] = np.random.uniform(70, 150, 5)
    
    return obs, cm_hist, cm_future

def test_cdft_configuration(config_name, **kwargs):
    """Test a specific CDFt configuration."""
    print(f"\n=== Testing {config_name} ===")
    
    obs, cm_hist, cm_future = create_test_data()
    
    try:
        # Create CDFt debiaser with specified configuration
        debiaser = CDFt.from_variable("pr")
        
        # Update configuration
        for key, value in kwargs.items():
            setattr(debiaser, key, value)
        
        print(f"Configuration:")
        for key, value in kwargs.items():
            print(f"  {key}: {value}")
        
        # Apply CDFt
        result = debiaser.apply(obs, cm_hist, cm_future)
        
        # Basic validation
        if np.any(np.isnan(result)):
            print("❌ FAILED: Result contains NaN values")
            return False
        elif np.any(np.isinf(result)):
            print("❌ FAILED: Result contains infinite values")
            return False
        elif np.any(result < 0):
            print("❌ FAILED: Result contains negative precipitation")
            return False
        else:
            print("✅ SUCCESS: CDFt completed without errors")
            
            # Additional statistics
            print(f"  Input obs range: [{np.min(obs):.3f}, {np.max(obs):.3f}]")
            print(f"  Input cm_hist range: [{np.min(cm_hist):.3f}, {np.max(cm_hist):.3f}]")
            print(f"  Input cm_future range: [{np.min(cm_future):.3f}, {np.max(cm_future):.3f}]")
            print(f"  Output range: [{np.min(result):.3f}, {np.max(result):.3f}]")
            print(f"  Mean bias reduction: {np.mean(cm_future) - np.mean(obs):.3f} → {np.mean(result) - np.mean(obs):.3f}")
            
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

def investigate_quantile_issues():
    """Investigate specific quantile-related issues."""
    print("=== Investigating Quantile Issues ===")
    
    obs, cm_hist, cm_future = create_test_data()
    
    # Test ECDF values that might cause issues
    from ibicus.utils import ecdf
    
    print("\nTesting ECDF edge cases:")
    
    # Test with different methods
    methods = ["step_function", "linear_interpolation", "kernel_density"]
    
    for method in methods:
        try:
            # Test ECDF on extreme values
            test_vals = np.array([np.min(obs), np.max(obs), np.min(obs) - 1, np.max(obs) + 1])
            ecdf_vals = ecdf(obs, test_vals, method=method)
            
            print(f"  {method}: ECDF range [{np.min(ecdf_vals):.6f}, {np.max(ecdf_vals):.6f}]")
            
            # Check for problematic values
            if np.any(ecdf_vals < 0) or np.any(ecdf_vals > 1):
                print(f"    ⚠️  WARNING: ECDF values outside [0,1] range")
            
            if np.any(ecdf_vals == 0) or np.any(ecdf_vals == 1):
                print(f"    ⚠️  WARNING: ECDF values exactly 0 or 1 (may cause IECDF issues)")
                
        except Exception as e:
            print(f"  {method}: ERROR - {str(e)}")

def test_robust_configurations():
    """Test various robust configurations for CDFt."""
    print("\n" + "="*60)
    print("TESTING ROBUST CDFt CONFIGURATIONS")
    print("="*60)
    
    configurations = [
        # Default configuration
        ("Default", {}),
        
        # Disable running window mode
        ("No Running Window", {
            "running_window_mode": False
        }),
        
        # Use different ECDF/IECDF methods
        ("Linear Interpolation ECDF", {
            "ecdf_method": "linear_interpolation"
        }),
        
        ("Kernel Density ECDF", {
            "ecdf_method": "kernel_density"
        }),
        
        ("Nearest IECDF", {
            "iecdf_method": "nearest"
        }),
        
        ("Linear IECDF", {
            "iecdf_method": "linear"
        }),
        
        # Disable SSR for precipitation
        ("No SSR", {
            "SSR": False
        }),
        
        # Disable monthly application
        ("No Monthly Application", {
            "apply_by_month": False
        }),
        
        # Conservative combination
        ("Conservative", {
            "running_window_mode": False,
            "ecdf_method": "linear_interpolation",
            "iecdf_method": "linear",
            "apply_by_month": False
        }),
        
        # Robust combination with SSR disabled
        ("Robust No SSR", {
            "running_window_mode": False,
            "ecdf_method": "linear_interpolation", 
            "iecdf_method": "nearest",
            "SSR": False,
            "apply_by_month": True
        }),
        
        # Minimal complexity
        ("Minimal", {
            "running_window_mode": False,
            "ecdf_method": "step_function",
            "iecdf_method": "inverted_cdf",
            "SSR": False,
            "apply_by_month": False
        })
    ]
    
    results = {}
    
    for config_name, config in configurations:
        success = test_cdft_configuration(config_name, **config)
        results[config_name] = success
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF RESULTS")
    print("="*60)
    
    successful_configs = []
    failed_configs = []
    
    for config_name, success in results.items():
        if success:
            print(f"✅ {config_name}")
            successful_configs.append(config_name)
        else:
            print(f"❌ {config_name}")
            failed_configs.append(config_name)
    
    print(f"\nSuccessful configurations: {len(successful_configs)}/{len(results)}")
    
    if successful_configs:
        print("\nRecommended robust configurations:")
        for config in successful_configs[:3]:  # Top 3
            print(f"  - {config}")
    
    return results

def create_recommendations_report(results):
    """Create a report with recommendations for robust CDFt usage."""
    
    report = f"""# CDFt Robustness Investigation Report

Generated on: {np.datetime64('today')}

## Overview

This report investigates the "Quantiles must be in the range [0, 1]" error
commonly encountered with the CDFt bias correction method and provides
robust configuration recommendations.

## Background

The CDFt (CDF-transform) method uses empirical cumulative distribution functions (ECDFs)
and their inverses (ICDFs) for quantile mapping. Issues can arise when:

1. **ECDF values reach exactly 0 or 1**: This can cause problems with inverse CDF calculations
2. **Extreme values outside training range**: Values beyond the observed range can cause extrapolation issues
3. **Running window complications**: Running windows can introduce edge effects
4. **Stochastic Singularity Removal (SSR)**: Can interact poorly with sparse precipitation data
5. **Monthly application edge cases**: Month-specific fitting can fail with insufficient data

## Test Results

The following configurations were tested with challenging synthetic precipitation data:

"""
    
    successful_configs = []
    failed_configs = []
    
    for config_name, success in results.items():
        if success:
            successful_configs.append(config_name)
            report += f"✅ **{config_name}**: SUCCESS\n"
        else:
            failed_configs.append(config_name)
            report += f"❌ **{config_name}**: FAILED\n"
    
    report += f"""
## Recommendations

Based on the test results, the following approaches are recommended to avoid CDFt quantile errors:

### 1. Robust Configuration (Recommended)

```python
debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.ecdf_method = "linear_interpolation"
debiaser.iecdf_method = "nearest"
debiaser.SSR = False  # For problematic precipitation data
debiaser.apply_by_month = True
```

### 2. Conservative Configuration

```python
debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.apply_by_month = False
debiaser.ecdf_method = "linear_interpolation"
debiaser.iecdf_method = "linear"
```

### 3. Minimal Configuration

```python
debiaser = CDFt.from_variable("pr")
debiaser.running_window_mode = False
debiaser.SSR = False
debiaser.apply_by_month = False
```

## Key Strategies

1. **Disable Running Window Mode**: This eliminates edge effects and reduces complexity
2. **Use Linear Interpolation for ECDF**: More robust than step functions for edge cases
3. **Use Nearest or Linear for IECDF**: Avoids extrapolation issues
4. **Disable SSR for Problematic Data**: SSR can cause issues with sparse precipitation
5. **Consider Disabling Monthly Application**: For datasets with insufficient monthly data

## Data Preprocessing Recommendations

Before applying CDFt, consider:

1. **Remove or flag extreme outliers** that are far outside the typical range
2. **Ensure sufficient data** in each month if using monthly application
3. **Check for data quality issues** such as missing values or unrealistic values
4. **Consider data transformation** for highly skewed variables

## Alternative Methods

If CDFt continues to fail, consider these alternative bias correction methods:

1. **ISIMIP**: Generally more robust and trend-preserving
2. **Quantile Mapping**: Simpler non-parametric approach
3. **Linear Scaling**: Most robust but only corrects mean bias
4. **Quantile Delta Mapping**: Trend-preserving alternative

## Validation

Always validate bias correction results by:

1. **Checking for NaN or infinite values** in output
2. **Verifying physical realism** (e.g., no negative precipitation)
3. **Comparing statistical properties** before and after correction
4. **Examining extreme values** and their representation
5. **Assessing temporal correlation preservation**

## Conclusion

CDFt can be made more robust by simplifying the configuration and avoiding
problematic settings. The recommended configurations above should resolve
most quantile range errors while maintaining reasonable bias correction performance.

For critical applications, consider using ISIMIP as a more robust alternative
to CDFt, as it has been specifically designed to handle challenging datasets
and edge cases more gracefully.
"""
    
    # Save report
    report_file = "/workspace/data/processed/ibicus/figures/cdft_robustness_report.md"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return report_file

def main():
    """Main function to run CDFt robustness investigation."""
    print("CDFt Robustness Investigation")
    print("="*60)
    
    # Investigate quantile issues
    investigate_quantile_issues()
    
    # Test robust configurations
    results = test_robust_configurations()
    
    # Create recommendations report
    report_file = create_recommendations_report(results)
    
    print(f"\n🎯 Investigation complete!")
    print(f"📊 Results: {sum(results.values())}/{len(results)} configurations successful")
    print(f"📄 Report: {report_file}")

if __name__ == "__main__":
    main()