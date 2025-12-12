#!/usr/bin/env python3
"""
Plot and compare distributions of original and ORBv3-predicted formation energies.
Simple histogram version with statistics.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

# Set style
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12

def load_data(csv_path):
    """Load the dataset and extract formation energies."""
    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Extract relevant columns
    original = df['formation_energy_per_atom'].dropna()
    orbv3 = df['formation_energy_per_atom_orbv3'].dropna()
    
    print(f"Loaded {len(df):,} structures")
    print(f"Original: {len(original):,} values")
    print(f"ORBv3: {len(orbv3):,} values")
    
    return original, orbv3, df

def calculate_statistics(original, orbv3, df):
    """Calculate statistical measures."""
    # Get paired data for correlation
    paired_df = df[['formation_energy_per_atom', 'formation_energy_per_atom_orbv3']].dropna()
    
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
        'orbv3': {
            'mean': orbv3.mean(),
            'std': orbv3.std(),
            'median': orbv3.median(),
            'min': orbv3.min(),
            'max': orbv3.max(),
            'q25': orbv3.quantile(0.25),
            'q75': orbv3.quantile(0.75),
            'count': len(orbv3)
        }
    }
    
    # Correlation and error metrics
    if len(paired_df) > 0:
        stats['correlation'] = paired_df['formation_energy_per_atom'].corr(
            paired_df['formation_energy_per_atom_orbv3']
        )
        stats['mae'] = np.abs(
            paired_df['formation_energy_per_atom'] - paired_df['formation_energy_per_atom_orbv3']
        ).mean()
        stats['rmse'] = np.sqrt(
            ((paired_df['formation_energy_per_atom'] - paired_df['formation_energy_per_atom_orbv3'])**2).mean()
        )
    
    return stats

def create_histogram_plot(original, orbv3, stats, output_path):
    """Create histogram plot with statistics and inset for positive region."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Determine bin range from both distributions for main plot (show full range)
    all_values = np.concatenate([original.values, orbv3.values])
    bin_min = min(all_values.min(), -6)
    bin_max = max(all_values.max(), 8)  # Show full range including positive values
    bins = np.linspace(bin_min, bin_max, 100)  # More bins for better resolution
    
    # Create histograms with density=True (like reference image)
    n1, bins1, patches1 = ax.hist(original, bins=bins, alpha=0.6, 
                                  label='Original (Reference)', 
                                  color='blue', edgecolor='black', linewidth=0.5,
                                  density=True)
    n2, bins2, patches2 = ax.hist(orbv3, bins=bins, alpha=0.6, 
                                 label='ORBv3 (Predicted)', 
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
    
    stats_text += f"ORBv3:\n"
    stats_text += f"  μ = {stats['orbv3']['mean']:.3f} eV/atom\n"
    stats_text += f"  σ = {stats['orbv3']['std']:.3f} eV/atom\n\n"
    
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

def print_summary(stats):
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
    
    print("\nORBv3 (Predicted) Formation Energy:")
    print(f"  Count: {stats['orbv3']['count']:,}")
    print(f"  Mean: {stats['orbv3']['mean']:.4f} eV/atom")
    print(f"  Std: {stats['orbv3']['std']:.4f} eV/atom")
    print(f"  Median: {stats['orbv3']['median']:.4f} eV/atom")
    print(f"  Range: [{stats['orbv3']['min']:.4f}, {stats['orbv3']['max']:.4f}] eV/atom")
    
    if 'correlation' in stats:
        print("\nComparison Metrics:")
        print(f"  Correlation: {stats['correlation']:.4f}")
        print(f"  Mean Absolute Error (MAE): {stats['mae']:.4f} eV/atom")
        print(f"  Root Mean Square Error (RMSE): {stats['rmse']:.4f} eV/atom")
    
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description='Plot and compare formation energy distributions'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        default='docs/benchmarks/train_encoded_decoded_orbv3.csv',
        help='Path to input CSV file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='docs/benchmarks/formation_energy_comparison.png',
        help='Path to output plot file'
    )
    
    args = parser.parse_args()
    
    # Load data
    original, orbv3, df = load_data(args.input)
    
    # Calculate statistics
    stats = calculate_statistics(original, orbv3, df)
    
    # Print summary
    print_summary(stats)
    
    # Create plot
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    create_histogram_plot(original, orbv3, stats, output_path)
    
    print(f"Analysis complete! Plot saved to: {output_path}")

if __name__ == '__main__':
    main()
