#!/usr/bin/env python3
"""
Generic script to plot and compare distributions of original and MLIP-predicted formation energies.
Supports any MLIP model (m3gnet, chgnet, mattersim, orbv3).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# Set style
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def load_data(csv_path, model="m3gnet"):
    """Load the dataset and extract formation energies."""
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Extract relevant columns
    original = df['formation_energy_per_atom'].dropna()
    model_key = model.lower()
    predicted_col = f'formation_energy_per_atom_{model_key}'
    
    if predicted_col not in df.columns:
        raise ValueError(f"Column '{predicted_col}' not found in CSV. Available columns: {list(df.columns)}")
    
    predicted = df[predicted_col].dropna()
    
    print(f"Loaded {len(df):,} structures")
    print(f"Original: {len(original):,} values")
    print(f"{model.upper()}: {len(predicted):,} values")
    
    return original, predicted, df, model

def calculate_statistics(original, predicted, df, model="m3gnet"):
    """Calculate statistical measures."""
    model_key = model.lower()
    predicted_col = f'formation_energy_per_atom_{model_key}'
    
    # Get paired data for correlation
    paired_df = df[['formation_energy_per_atom', predicted_col]].dropna()
    
    stats = {
        'original': {
            'mean': original.mean(),
            'std': original.std(),
            'median': original.median(),
            'min': original.min(),
            'max': original.max(),
            'q25': original.quantile(0.25),
            'q75': original.quantile(0.75),
            'count': len(original)
        },
        'predicted': {
            'mean': predicted.mean(),
            'std': predicted.std(),
            'median': predicted.median(),
            'min': predicted.min(),
            'max': predicted.max(),
            'q25': predicted.quantile(0.25),
            'q75': predicted.quantile(0.75),
            'count': len(predicted)
        }
    }
    
    # Correlation and error metrics
    if len(paired_df) > 0:
        stats['correlation'] = paired_df['formation_energy_per_atom'].corr(
            paired_df[predicted_col]
        )
        stats['mae'] = np.abs(
            paired_df['formation_energy_per_atom'] - paired_df[predicted_col]
        ).mean()
        stats['rmse'] = np.sqrt(
            ((paired_df['formation_energy_per_atom'] - paired_df[predicted_col])**2).mean()
        )
    
    return stats

def create_histogram_plot(original, predicted, stats, output_path, model="m3gnet"):
    """Create histogram plot with statistics and inset for positive region."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Determine bin range from both distributions for main plot (show full range)
    all_values = np.concatenate([original.values, predicted.values])
    bin_min = min(all_values.min(), -6)
    bin_max = max(all_values.max(), 8)  # Show full range including positive values
    bins = np.linspace(bin_min, bin_max, 100)  # More bins for better resolution
    
    # Create histograms with density=True (like reference image)
    n1, bins1, patches1 = ax.hist(original, bins=bins, alpha=0.6, 
                                  label='Original (Reference)', 
                                  color='blue', edgecolor='black', linewidth=0.5,
                                  density=True)
    n2, bins2, patches2 = ax.hist(predicted, bins=bins, alpha=0.6, 
                                 label=f'{model.upper()} (Predicted)', 
                                 color='red', edgecolor='black', linewidth=0.5,
                                 density=True)
    
    # Labels (no title)
    ax.set_xlabel('Formation Energy per Atom (eV/atom)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Density', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    
    # Create comparison statistics text box (similar to reference style)
    stats_text = ""
    stats_text += f"Original:\n"
    stats_text += f"  μ = {stats['original']['mean']:.3f} eV/atom\n"
    stats_text += f"  σ = {stats['original']['std']:.3f} eV/atom\n\n"
    
    stats_text += f"{model.upper()}:\n"
    stats_text += f"  μ = {stats['predicted']['mean']:.3f} eV/atom\n"
    stats_text += f"  σ = {stats['predicted']['std']:.3f} eV/atom\n\n"
    
    if 'correlation' in stats:
        stats_text += f"Pearson r = {stats['correlation']:.4f}\n"
        stats_text += f"MAE = {stats['mae']:.4f} eV/atom\n"
        stats_text += f"RMSE = {stats['rmse']:.4f} eV/atom"
    
    # Add text box with statistics (top-left like reference)
    props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black', linewidth=1.5)
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=props)
    
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")
    
    return fig

def print_summary(stats, model="m3gnet"):
    """Print summary statistics to console."""
    print("\n" + "="*70)
    print("FORMATION ENERGY DISTRIBUTION COMPARISON")
    print("="*70)
    print("\nOriginal (Reference) Formation Energy:")
    print(f"  Count: {stats['original']['count']:,}")
    print(f"  Mean: {stats['original']['mean']:.4f} eV/atom")
    print(f"  Std: {stats['original']['std']:.4f} eV/atom")
    print(f"  Median: {stats['original']['median']:.4f} eV/atom")
    print(f"  Range: [{stats['original']['min']:.4f}, {stats['original']['max']:.4f}] eV/atom")
    
    print(f"\n{model.upper()} (Predicted) Formation Energy:")
    print(f"  Count: {stats['predicted']['count']:,}")
    print(f"  Mean: {stats['predicted']['mean']:.4f} eV/atom")
    print(f"  Std: {stats['predicted']['std']:.4f} eV/atom")
    print(f"  Median: {stats['predicted']['median']:.4f} eV/atom")
    print(f"  Range: [{stats['predicted']['min']:.4f}, {stats['predicted']['max']:.4f}] eV/atom")
    
    if 'correlation' in stats:
        print("\nComparison Metrics:")
        print(f"  Correlation: {stats['correlation']:.4f}")
        print(f"  Mean Absolute Error (MAE): {stats['mae']:.4f} eV/atom")
        print(f"  Root Mean Square Error (RMSE): {stats['rmse']:.4f} eV/atom")
    
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='Plot and compare formation energy distributions for any MLIP model'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='benchmark/results/data/train_encoded_decoded_orbv3.csv',
        help='Path to input CSV file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Path to output plot file (auto-generated if not specified)'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='m3gnet',
        choices=['m3gnet', 'chgnet', 'mattersim', 'orbv3'],
        help='MLIP model name'
    )
    
    args = parser.parse_args()
    
    # Auto-generate output path if not specified
    if args.output is None:
        args.output = f'benchmark/results/images/formation_energy_comparison_{args.model}.png'
    
    # Load data
    original, predicted, df, model = load_data(args.input, args.model)
    
    # Calculate statistics
    stats = calculate_statistics(original, predicted, df, args.model)
    
    # Print summary
    print_summary(stats, args.model)
    
    # Create plot
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    create_histogram_plot(original, predicted, stats, output_path, args.model)
    
    print(f"Analysis complete! Plot saved to: {output_path}")

if __name__ == '__main__':
    main()
