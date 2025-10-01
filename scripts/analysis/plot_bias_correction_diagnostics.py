#!/usr/bin/env python3
"""
Generate bias-correction diagnostics consistent with ibicus examples.

Inputs (searched by filename anywhere under the workspace if paths not provided):
  - obs_pr_1980_2005_on_model_grid.nc
  - cm_hist_pr_1980_2005.nc
  - debiased_pr_2001_2005_isimip.nc

Outputs:
  - Figures saved under the specified output directory (default: /workspace/data/processed/ibicus/figures)
  - figures_index.md listing generated figures

Notes:
  - Handles precipitation unit conversion from kg m-2 s-1 to mm/day where possible.
  - Restricts most comparisons to the temporal overlap of all inputs.
  - Robust to missing files: script logs issues and creates an index regardless.
"""

import argparse
import os
import sys
import glob
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import xarray as xr
except Exception as e:  # pragma: no cover
    print("ERROR: xarray is required. Install with: pip install xarray", file=sys.stderr)
    raise

try:
    import pandas as pd
except Exception as e:  # pragma: no cover
    print("ERROR: pandas is required. Install with: pip install pandas", file=sys.stderr)
    raise

import matplotlib

# Use a non-interactive backend so this can run headless.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


DEFAULT_OUTPUT_DIR = "/workspace/data/processed/ibicus/figures"
WORKSPACE_ROOT = "/workspace"


def discover_file_by_name(filename: str, search_root: str = WORKSPACE_ROOT) -> Optional[str]:
    """Attempt to locate a file by name anywhere under the workspace.

    Returns the absolute path if found, else None.
    """
    candidates = glob.glob(os.path.join(search_root, "**", filename), recursive=True)
    if candidates:
        # Prefer shortest path (closest) deterministically
        candidates_sorted = sorted(candidates, key=lambda p: len(p))
        return os.path.abspath(candidates_sorted[0])
    return None


def resolve_input_path(maybe_path: Optional[str], fallback_filename: str) -> Optional[str]:
    if maybe_path and os.path.exists(maybe_path):
        return os.path.abspath(maybe_path)
    return discover_file_by_name(fallback_filename)


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def pick_variable_name(dataset: xr.Dataset, preferred_names: Sequence[str]) -> str:
    """Pick a data variable from a dataset.

    Preference order: preferred_names (e.g., ['pr']), then the first data variable.
    Raises if none found.
    """
    for name in preferred_names:
        if name in dataset.data_vars:
            return name
    data_vars = list(dataset.data_vars)
    if not data_vars:
        raise ValueError("No data variables found in dataset")
    return data_vars[0]


def convert_precip_to_mm_per_day(data_array: xr.DataArray) -> xr.DataArray:
    """Convert precipitation to mm/day if units are kg m-2 s-1.

    If units are missing or unknown, data is returned unchanged.
    """
    units = str(data_array.attrs.get("units", "")).strip().lower()
    if units in {"kg m-2 s-1", "kg m-2 s^-1", "kg/m^2/s", "kg m**-2 s**-1"}:
        converted = data_array * 86400.0  # 1 kg/m^2/s == 1 mm/s; 86400 s/day
        converted.attrs["units"] = "mm/day"
        return converted
    if units == "mm/s":
        converted = data_array * 86400.0
        converted.attrs["units"] = "mm/day"
        return converted
    # Assume already mm/day or similar
    return data_array


def _get_time_dim_name(data_array: xr.DataArray) -> str:
    for dim in data_array.dims:
        if dim.lower() == "time":
            return dim
    raise ValueError("No 'time' dimension found in data array")


def align_time_overlap(obs: xr.DataArray, raw: xr.DataArray, deb: Optional[xr.DataArray]) -> Tuple[xr.DataArray, xr.DataArray, Optional[xr.DataArray]]:
    """Align arrays to their overlapping time period using inner join.

    Returns copies aligned on time. If deb is None, aligns obs and raw only.
    """
    if deb is None:
        obs_aligned, raw_aligned = xr.align(obs, raw, join="inner")
        return obs_aligned, raw_aligned, None
    obs_aligned, raw_aligned, deb_aligned = xr.align(obs, raw, deb, join="inner")
    return obs_aligned, raw_aligned, deb_aligned


def select_representative_point(data_array: xr.DataArray) -> xr.DataArray:
    """Select a representative grid point (middle indices) for time series plots."""
    spatial_dims = [d for d in data_array.dims if d.lower() not in {"time"}]
    selection = {}
    for dim in spatial_dims:
        coord = data_array.coords[dim]
        mid_index = int(coord.size // 2)
        selection[dim] = coord[mid_index]
    return data_array.sel(**selection)


def flatten_time_and_space(data_array: xr.DataArray) -> np.ndarray:
    """Flatten all non-NaN values across time and space into a 1D array."""
    values = data_array.values.ravel()
    values = values[np.isfinite(values)]
    return values


def compute_ecdf(values: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Compute empirical CDF (x, F(x))."""
    if values.size == 0:
        return np.array([]), np.array([])
    x = np.sort(values)
    y = np.arange(1, x.size + 1, dtype=float) / float(x.size)
    return x, y


def qq_data(reference: np.ndarray, candidate: np.ndarray, num_quantiles: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """Return pairs (ref_q, cand_q) along a quantile grid."""
    if reference.size == 0 or candidate.size == 0:
        return np.array([]), np.array([])
    q = np.linspace(0.001, 0.999, num_quantiles)
    ref_q = np.quantile(reference, q)
    cand_q = np.quantile(candidate, q)
    return ref_q, cand_q


def monthly_means(data_array: xr.DataArray) -> pd.Series:
    time_dim = _get_time_dim_name(data_array)
    grouped = data_array.groupby(f"{time_dim}.month").mean()
    # Convert to pandas for easy plotting order
    s = grouped.to_series()
    s.index = s.index.astype(int)
    s = s.sort_index()
    return s


def wet_day_frequency(data_array: xr.DataArray, threshold_mm_per_day: float = 1.0) -> float:
    """Return fraction of wet days across time and space given a threshold in mm/day."""
    time_dim = _get_time_dim_name(data_array)
    # Count wet days per grid cell
    is_wet = (data_array >= threshold_mm_per_day)
    wet_days_per_cell = is_wet.sum(dim=time_dim)
    total_days_per_cell = data_array[time_dim].size
    fraction_per_cell = wet_days_per_cell / float(total_days_per_cell)
    # Aggregate by spatial average
    return float(fraction_per_cell.mean().values)


def percentile(values: np.ndarray, p: float) -> float:
    if values.size == 0:
        return np.nan
    return float(np.nanpercentile(values, p))


def figure_path(output_dir: str, name: str) -> str:
    return os.path.join(output_dir, name)


def save_figure(fig: plt.Figure, path: str) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_hist_ecdf(obs_vals: np.ndarray, raw_vals: np.ndarray, deb_vals: Optional[np.ndarray], output_dir: str, prefix: str = "pr") -> List[str]:
    saved = []
    # Histograms
    fig, ax = plt.subplots(figsize=(8, 5))
    bins = 50
    sns.histplot(obs_vals, bins=bins, color="black", label="Obs", stat="density", element="step", fill=False, ax=ax)
    sns.histplot(raw_vals, bins=bins, color="tab:orange", label="Raw", stat="density", element="step", fill=False, ax=ax)
    if deb_vals is not None:
        sns.histplot(deb_vals, bins=bins, color="tab:green", label="Debiased", stat="density", element="step", fill=False, ax=ax)
    ax.set_title("Histogram: Pre/Post")
    ax.set_xlabel("Precip (mm/day)")
    ax.legend()
    out = figure_path(output_dir, f"{prefix}_hist_pre_post.png")
    save_figure(fig, out)
    saved.append(out)

    # ECDFs
    fig, ax = plt.subplots(figsize=(8, 5))
    for vals, label, color in [
        (obs_vals, "Obs", "black"),
        (raw_vals, "Raw", "tab:orange"),
        (deb_vals, "Debiased", "tab:green"),
    ]:
        if vals is None:
            continue
        x, y = compute_ecdf(vals)
        if x.size == 0:
            continue
        ax.plot(x, y, label=label, color=color)
    ax.set_title("ECDF: Pre/Post")
    ax.set_xlabel("Precip (mm/day)")
    ax.set_ylabel("F(x)")
    ax.legend()
    out = figure_path(output_dir, f"{prefix}_ecdf_pre_post.png")
    save_figure(fig, out)
    saved.append(out)
    return saved


def plot_qq(obs_vals: np.ndarray, other_vals: np.ndarray, label: str, output_dir: str, prefix: str = "pr") -> str:
    ref_q, cand_q = qq_data(obs_vals, other_vals)
    fig, ax = plt.subplots(figsize=(5, 5))
    if ref_q.size > 0:
        ax.scatter(ref_q, cand_q, s=10, alpha=0.5)
    lims = [np.nanmin([ref_q.min() if ref_q.size else 0.0, cand_q.min() if cand_q.size else 0.0]),
            np.nanmax([ref_q.max() if ref_q.size else 1.0, cand_q.max() if cand_q.size else 1.0])]
    if np.isfinite(lims).all():
        ax.plot(lims, lims, color="black", linewidth=1.0, linestyle="--")
        ax.set_xlim(lims)
        ax.set_ylim(lims)
    ax.set_title(f"QQ: Obs vs {label}")
    ax.set_xlabel("Obs quantiles (mm/day)")
    ax.set_ylabel(f"{label} quantiles (mm/day)")
    out = figure_path(output_dir, f"{prefix}_qq_obs_vs_{label.lower().replace(' ', '_')}.png")
    save_figure(fig, out)
    return out


def plot_seasonal_cycle(obs: xr.DataArray, raw: xr.DataArray, deb: Optional[xr.DataArray], output_dir: str, prefix: str = "pr") -> str:
    obs_monthly = monthly_means(obs)
    raw_monthly = monthly_means(raw)
    deb_monthly = monthly_means(deb) if deb is not None else None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(obs_monthly.index, obs_monthly.values, marker="o", label="Obs", color="black")
    ax.plot(raw_monthly.index, raw_monthly.values, marker="o", label="Raw", color="tab:orange")
    if deb_monthly is not None:
        ax.plot(deb_monthly.index, deb_monthly.values, marker="o", label="Debiased", color="tab:green")
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Month")
    ax.set_ylabel("Precip (mm/day)")
    ax.set_title("Seasonal cycle (monthly means)")
    ax.legend()
    out = figure_path(output_dir, f"{prefix}_seasonal_cycle.png")
    save_figure(fig, out)
    return out


def plot_wet_day_frequency_bars(obs: xr.DataArray, raw: xr.DataArray, deb: Optional[xr.DataArray], output_dir: str, threshold: float = 1.0, prefix: str = "pr") -> str:
    obs_frac = wet_day_frequency(obs, threshold)
    raw_frac = wet_day_frequency(raw, threshold)
    deb_frac = wet_day_frequency(deb, threshold) if deb is not None else np.nan

    labels = ["Obs", "Raw", "Debiased"] if deb is not None else ["Obs", "Raw"]
    values = [obs_frac, raw_frac, deb_frac] if deb is not None else [obs_frac, raw_frac]

    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(x=labels, y=values, palette=["black", "tab:orange", "tab:green"][: len(labels)], ax=ax)
    ax.set_ylabel("Wet-day frequency")
    ax.set_title(f"Wet-day frequency (threshold {threshold} mm/day)")
    out = figure_path(output_dir, f"{prefix}_wetday_frequency.png")
    save_figure(fig, out)
    return out


def plot_extreme_tails(obs_vals: np.ndarray, raw_vals: np.ndarray, deb_vals: Optional[np.ndarray], output_dir: str, prefix: str = "pr") -> str:
    metrics = [
        ("P95", 95.0),
        ("P99", 99.0),
    ]
    rows = []
    for name, p in metrics:
        rows.append((name, percentile(obs_vals, p), percentile(raw_vals, p), percentile(deb_vals, p) if deb_vals is not None else np.nan))
    labels = [r[0] for r in rows]
    obs_list = [r[1] for r in rows]
    raw_list = [r[2] for r in rows]
    deb_list = [r[3] for r in rows]

    x = np.arange(len(labels))
    width = 0.25
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - width, obs_list, width=width, label="Obs", color="black")
    ax.bar(x, raw_list, width=width, label="Raw", color="tab:orange")
    if deb_vals is not None:
        ax.bar(x + width, deb_list, width=width, label="Debiased", color="tab:green")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("mm/day")
    ax.set_title("Extreme tails comparison")
    ax.legend()
    out = figure_path(output_dir, f"{prefix}_extreme_tails.png")
    save_figure(fig, out)
    return out


def plot_sample_time_series(obs: xr.DataArray, raw: xr.DataArray, deb: Optional[xr.DataArray], output_dir: str, prefix: str = "pr") -> str:
    obs_pt = select_representative_point(obs)
    raw_pt = select_representative_point(raw)
    deb_pt = select_representative_point(deb) if deb is not None else None

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(obs_pt[obs_pt.dims[0]].values, obs_pt.values, label="Obs", color="black", linewidth=0.8)
    ax.plot(raw_pt[raw_pt.dims[0]].values, raw_pt.values, label="Raw", color="tab:orange", linewidth=0.8)
    if deb_pt is not None:
        ax.plot(deb_pt[deb_pt.dims[0]].values, deb_pt.values, label="Debiased", color="tab:green", linewidth=0.8)
    ax.set_title("Sample time series (representative point)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Precip (mm/day)")
    ax.legend(ncol=3)
    out = figure_path(output_dir, f"{prefix}_sample_time_series.png")
    save_figure(fig, out)
    return out


def plot_scatter_obs_vs(obs_vals: np.ndarray, other_vals: np.ndarray, label: str, output_dir: str, prefix: str = "pr") -> str:
    # Match sizes by truncation to smallest length just in case
    n = min(obs_vals.size, other_vals.size)
    obs_v = obs_vals[:n]
    oth_v = other_vals[:n]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(obs_v, oth_v, s=5, alpha=0.5)
    min_v = float(np.nanmin([obs_v.min(initial=0.0), oth_v.min(initial=0.0)]))
    max_v = float(np.nanmax([obs_v.max(initial=1.0), oth_v.max(initial=1.0)]))
    ax.plot([min_v, max_v], [min_v, max_v], linestyle="--", color="black")
    ax.set_xlabel("Obs (mm/day)")
    ax.set_ylabel(f"{label} (mm/day)")
    ax.set_title(f"Scatter: Obs vs {label}")
    out = figure_path(output_dir, f"{prefix}_scatter_obs_vs_{label.lower().replace(' ', '_')}.png")
    save_figure(fig, out)
    return out


def write_figures_index(output_dir: str, figure_paths: List[str]) -> str:
    index_path = os.path.join(output_dir, "figures_index.md")
    lines = [
        "### Ibicus Bias Correction Diagnostics\n",
        "\n",
        "Figures generated by plot_bias_correction_diagnostics.py:\n",
        "\n",
    ]
    if not figure_paths:
        lines.append("- No figures were generated. Check input files and dependencies.\n")
    else:
        for p in sorted(figure_paths):
            rel = os.path.relpath(p, output_dir)
            lines.append(f"- {rel}\n")
    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return index_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate bias correction diagnostics.")
    parser.add_argument("--obs", type=str, default=None, help="Path to obs_pr_1980_2005_on_model_grid.nc")
    parser.add_argument("--raw", type=str, default=None, help="Path to cm_hist_pr_1980_2005.nc")
    parser.add_argument("--deb", type=str, default=None, help="Path to debiased_pr_2001_2005_isimip.nc")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory to save figures")
    parser.add_argument("--wet-threshold", type=float, default=1.0, help="Wet-day threshold in mm/day")
    args = parser.parse_args(argv)

    ensure_output_dir(args.output_dir)

    obs_path = resolve_input_path(args.obs, "obs_pr_1980_2005_on_model_grid.nc")
    raw_path = resolve_input_path(args.raw, "cm_hist_pr_1980_2005.nc")
    deb_path = resolve_input_path(args.deb, "debiased_pr_2001_2005_isimip.nc")

    missing = []
    if not obs_path:
        missing.append("obs_pr_1980_2005_on_model_grid.nc")
    if not raw_path:
        missing.append("cm_hist_pr_1980_2005.nc")
    if not deb_path:
        print("WARNING: Debiased file not found; proceeding with pre-only diagnostics.")

    figures: List[str] = []

    if missing:
        print("ERROR: Missing required inputs:")
        for m in missing:
            print(f" - {m}")
        index_path = write_figures_index(args.output_dir, figures)
        print(f"Wrote index: {index_path}")
        return 0  # Exit gracefully; environment may not have data yet

    print(f"Loading obs: {obs_path}")
    obs_ds = xr.open_dataset(obs_path)
    print(f"Loading raw: {raw_path}")
    raw_ds = xr.open_dataset(raw_path)
    deb_ds = None
    if deb_path:
        print(f"Loading debiased: {deb_path}")
        deb_ds = xr.open_dataset(deb_path)

    obs_var = pick_variable_name(obs_ds, ["pr"])  # precipitation
    raw_var = pick_variable_name(raw_ds, ["pr"])  # precipitation
    deb_var = pick_variable_name(deb_ds, ["pr"]) if deb_ds is not None else None

    obs = convert_precip_to_mm_per_day(obs_ds[obs_var])
    raw = convert_precip_to_mm_per_day(raw_ds[raw_var])
    deb = convert_precip_to_mm_per_day(deb_ds[deb_var]) if deb_ds is not None else None

    # Align overlap
    obs_al, raw_al, deb_al = align_time_overlap(obs, raw, deb)

    # Flatten for distribution-based diagnostics
    obs_vals = flatten_time_and_space(obs_al)
    raw_vals = flatten_time_and_space(raw_al)
    deb_vals = flatten_time_and_space(deb_al) if deb_al is not None else None

    print("Generating histograms and ECDFs...")
    figures.extend(plot_hist_ecdf(obs_vals, raw_vals, deb_vals, args.output_dir))

    print("Generating QQ plots...")
    figures.append(plot_qq(obs_vals, raw_vals, label="Raw", output_dir=args.output_dir))
    if deb_vals is not None:
        figures.append(plot_qq(obs_vals, deb_vals, label="Debiased", output_dir=args.output_dir))

    print("Generating seasonal cycle plot...")
    figures.append(plot_seasonal_cycle(obs_al, raw_al, deb_al, args.output_dir))

    print("Generating wet-day frequency bars...")
    figures.append(plot_wet_day_frequency_bars(obs_al, raw_al, deb_al, args.output_dir, threshold=args.wet_threshold))

    print("Generating extreme tails comparison...")
    figures.append(plot_extreme_tails(obs_vals, raw_vals, deb_vals, args.output_dir))

    print("Generating sample time series plot...")
    figures.append(plot_sample_time_series(obs_al, raw_al, deb_al, args.output_dir))

    print("Generating scatter plots...")
    figures.append(plot_scatter_obs_vs(obs_vals, raw_vals, label="Raw", output_dir=args.output_dir))
    if deb_vals is not None:
        figures.append(plot_scatter_obs_vs(obs_vals, deb_vals, label="Debiased", output_dir=args.output_dir))

    index_path = write_figures_index(args.output_dir, figures)
    print(f"Saved {len(figures)} figures to {args.output_dir}")
    print(f"Wrote index: {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

