#!/usr/bin/env python3
"""
Script to generate illustrations for SLICES documentation.
Generates visualizations of graph topology, strategies, and algorithms.

Requirements:
    pip install numpy matplotlib networkx
"""

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
    from matplotlib.collections import LineCollection
    import networkx as nx
    from pathlib import Path
except ImportError as e:
    print(f"Error: Missing required package. Please install: pip install numpy matplotlib networkx")
    print(f"Missing: {e}")
    exit(1)

# Create output directory
output_dir = Path("docs/illustrations")
output_dir.mkdir(parents=True, exist_ok=True)

def plot_strategy_comparison():
    """Illustrate the differences between SLICES encoding strategies."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('SLICES Encoding Strategies Comparison', fontsize=16, fontweight='bold')
    
    # Example structure: 3 atoms, 3 edges
    atoms = ['Si', 'O', 'Si']
    edges = [(0, 1, [0, 0, 0]), (1, 2, [1, 0, 0]), (0, 2, [0, 0, 0])]
    
    # Strategy 1
    ax = axes[0, 0]
    ax.set_title('Strategy 1: Edge-First Format', fontweight='bold')
    ax.text(0.1, 0.9, 'Format:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.1, 0.8, '[Atom1] [Atom2] [i] [j] [-/o/+] [-/o/+] [-/o/+]', 
            fontsize=10, family='monospace', transform=ax.transAxes)
    ax.text(0.1, 0.6, 'Example:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    example1 = "Si O 0 1 o o o\nSi O 1 2 + o o\nSi Si 0 2 o o o"
    ax.text(0.1, 0.4, example1, fontsize=9, family='monospace', 
            transform=ax.transAxes, verticalalignment='top')
    ax.text(0.1, 0.15, '• Atom symbols embedded with each edge\n• Edge indices explicit\n• Periodic labels space-separated',
            fontsize=9, transform=ax.transAxes)
    ax.axis('off')
    
    # Strategy 2
    ax = axes[0, 1]
    ax.set_title('Strategy 2: Compact Format', fontweight='bold')
    ax.text(0.1, 0.9, 'Format:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.1, 0.8, '[Atom1][Atom2]...[AtomN][i1j1][-o+][i2j2][-o+]...', 
            fontsize=10, family='monospace', transform=ax.transAxes)
    ax.text(0.1, 0.6, 'Example:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    example2 = "Si_O_Si0101ooo1212+oo0202ooo"
    ax.text(0.1, 0.4, example2, fontsize=9, family='monospace', 
            transform=ax.transAxes, verticalalignment='top')
    ax.text(0.1, 0.15, '• Atom symbols concatenated (2 chars)\n• Edge indices zero-padded\n• Periodic labels concatenated',
            fontsize=9, transform=ax.transAxes)
    ax.axis('off')
    
    # Strategy 3
    ax = axes[1, 0]
    ax.set_title('Strategy 3: Standard Format', fontweight='bold')
    ax.text(0.1, 0.9, 'Format:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.1, 0.8, '[Atom1] [Atom2] ... [AtomN] [i] [j] [-/o/+] [-/o/+] [-/o/+]', 
            fontsize=10, family='monospace', transform=ax.transAxes)
    ax.text(0.1, 0.6, 'Example:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    example3 = "Si O Si 0 1 o o o 1 2 + o o 0 2 o o o"
    ax.text(0.1, 0.4, example3, fontsize=9, family='monospace', 
            transform=ax.transAxes, verticalalignment='top')
    ax.text(0.1, 0.15, '• Atom symbols listed first\n• Then edges with indices\n• Periodic labels space-separated',
            fontsize=9, transform=ax.transAxes)
    ax.axis('off')
    
    # Strategy 4
    ax = axes[1, 1]
    ax.set_title('Strategy 4: Tokenized Format (Recommended)', fontweight='bold', color='green')
    ax.text(0.1, 0.9, 'Format:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.1, 0.8, '[Tokenized_SG] [Atom1] [Atom2] ... [AtomN] [i] [j] [-o+] ...', 
            fontsize=10, family='monospace', transform=ax.transAxes)
    ax.text(0.1, 0.6, 'Example:', fontsize=12, fontweight='bold', transform=ax.transAxes)
    example4 = "Si O Si 0 1 ooo 1 2 +oo 0 2 ooo"
    ax.text(0.1, 0.4, example4, fontsize=9, family='monospace', 
            transform=ax.transAxes, verticalalignment='top')
    ax.text(0.1, 0.15, '• Optional tokenized space group\n• Atom symbols listed first\n• Periodic labels concatenated',
            fontsize=9, transform=ax.transAxes)
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'strategies_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated: {output_dir / 'strategies_comparison.png'}")

def plot_graph_topology_check():
    """Illustrate graph topology periodicity checking using homology groups."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Graph Topology Periodicity Check: H₁(X,ℤ) Rank', fontsize=16, fontweight='bold')
    
    # Example 1: H1 = 0 (Tree, 0D)
    ax = axes[0]
    G1 = nx.Graph()
    G1.add_edges_from([(0, 1), (1, 2), (2, 3)])
    pos1 = nx.spring_layout(G1, seed=42)
    nx.draw(G1, pos1, ax=ax, with_labels=True, node_color='lightblue', 
            node_size=800, font_size=12, font_weight='bold', edge_color='gray', width=2)
    ax.set_title('H₁(X,ℤ) = 0\n(Tree, No Cycles)\n❌ Cannot create 3D embedding', 
                 fontweight='bold', color='red')
    ax.text(0.5, -0.15, '|E| = 3, |E₁| = 3\nb = 3 - 3 = 0', 
            ha='center', transform=ax.transAxes, fontsize=10)
    
    # Example 2: H1 = 2 (2D)
    ax = axes[1]
    G2 = nx.Graph()
    G2.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)])
    pos2 = nx.spring_layout(G2, seed=42)
    nx.draw(G2, pos2, ax=ax, with_labels=True, node_color='lightyellow', 
            node_size=800, font_size=12, font_weight='bold', edge_color='gray', width=2)
    ax.set_title('H₁(X,ℤ) = 2\n(Two Independent Cycles)\n❌ Cannot create 3D embedding', 
                 fontweight='bold', color='orange')
    ax.text(0.5, -0.15, '|E| = 5, |E₁| = 3\nb = 5 - 3 = 2', 
            ha='center', transform=ax.transAxes, fontsize=10)
    
    # Example 3: H1 = 3 (3D)
    ax = axes[2]
    G3 = nx.Graph()
    # Create a 3D-like structure (tetrahedron-like)
    G3.add_edges_from([(0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3)])
    pos3 = nx.spring_layout(G3, seed=42, k=2)
    nx.draw(G3, pos3, ax=ax, with_labels=True, node_color='lightgreen', 
            node_size=800, font_size=12, font_weight='bold', edge_color='gray', width=2)
    ax.set_title('H₁(X,ℤ) = 3\n(Three Independent Cycles)\n✅ Can create 3D embedding', 
                 fontweight='bold', color='green')
    ax.text(0.5, -0.15, '|E| = 6, |E₁| = 3\nb = 6 - 3 = 3', 
            ha='center', transform=ax.transAxes, fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'graph_topology_check.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated: {output_dir / 'graph_topology_check.png'}")

def plot_encoding_workflow():
    """Illustrate the SLICES encoding workflow."""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    
    # Title
    ax.text(5, 5.5, 'SLICES Encoding Workflow', ha='center', fontsize=18, fontweight='bold')
    
    # Step 1: Structure
    box1 = FancyBboxPatch((0.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(box1)
    ax.text(1.4, 4.4, 'Crystal\nStructure', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 1
    arrow1 = FancyArrowPatch((2.3, 4.4), (3.2, 4.4), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow1)
    ax.text(2.75, 4.7, '1. Graph\nConstruction', ha='center', fontsize=9, 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 2: Graph
    box2 = FancyBboxPatch((3.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightgreen', edgecolor='black', linewidth=2)
    ax.add_patch(box2)
    ax.text(4.4, 4.4, 'Labeled\nQuotient\nGraph', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 2
    arrow2 = FancyArrowPatch((5.3, 4.4), (6.2, 4.4), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow2)
    ax.text(5.75, 4.7, '2. Canonical\nLabeling', ha='center', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 3: Canonical Graph
    box3 = FancyBboxPatch((6.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightyellow', edgecolor='black', linewidth=2)
    ax.add_patch(box3)
    ax.text(7.4, 4.4, 'Canonical\nGraph', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 3 (down)
    arrow3 = FancyArrowPatch((7.4, 4), (7.4, 3.2), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow3)
    ax.text(7.7, 3.6, '3. String\nGeneration', ha='left', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 4: SLICES String
    box4 = FancyBboxPatch((5.5, 2.5), 3.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightcoral', edgecolor='black', linewidth=2)
    ax.add_patch(box4)
    ax.text(7.4, 2.9, 'SLICES String', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Details box
    detail_box = FancyBboxPatch((0.5, 0.5), 9, 1.5, boxstyle="round,pad=0.2", 
                               facecolor='white', edgecolor='gray', linewidth=1, linestyle='--')
    ax.add_patch(detail_box)
    ax.text(5, 1.7, 'SLICES String Components:', ha='center', fontsize=12, fontweight='bold')
    ax.text(5, 1.3, '• Atom symbols (element names)', ha='center', fontsize=10)
    ax.text(5, 1.0, '• Edge indices (atom pairs: i, j)', ha='center', fontsize=10)
    ax.text(5, 0.7, '• Edge labels (periodic boundary conditions: -, o, +)', ha='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'encoding_workflow.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated: {output_dir / 'encoding_workflow.png'}")

def plot_decoding_workflow():
    """Illustrate the SLICES decoding workflow."""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    
    # Title
    ax.text(5, 5.5, 'SLICES Decoding Workflow', ha='center', fontsize=18, fontweight='bold')
    
    # Step 1: SLICES String
    box1 = FancyBboxPatch((0.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightcoral', edgecolor='black', linewidth=2)
    ax.add_patch(box1)
    ax.text(1.4, 4.4, 'SLICES\nString', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 1
    arrow1 = FancyArrowPatch((2.3, 4.4), (3.2, 4.4), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow1)
    ax.text(2.75, 4.7, '1. Parse', ha='center', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 2: Graph
    box2 = FancyBboxPatch((3.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightgreen', edgecolor='black', linewidth=2)
    ax.add_patch(box2)
    ax.text(4.4, 4.4, 'Graph\nTopology', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 2
    arrow2 = FancyArrowPatch((5.3, 4.4), (6.2, 4.4), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow2)
    ax.text(5.75, 4.7, '2. XTB\nCalculation', ha='center', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 3: XTB
    box3 = FancyBboxPatch((6.5, 4), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightblue', edgecolor='black', linewidth=2)
    ax.add_patch(box3)
    ax.text(7.4, 4.4, 'Bond/Angle\nParameters', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 3 (down)
    arrow3 = FancyArrowPatch((7.4, 4), (7.4, 3.2), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow3)
    ax.text(7.7, 3.6, '3. Barycentric\nEmbedding', ha='left', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 4: Initial Structure
    box4 = FancyBboxPatch((5.5, 2.5), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightyellow', edgecolor='black', linewidth=2)
    ax.add_patch(box4)
    ax.text(6.4, 2.9, 'Initial\nStructure', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 4
    arrow4 = FancyArrowPatch((7.3, 2.9), (8.2, 2.9), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow4)
    ax.text(7.75, 3.2, '4. ZL*\nOptimization', ha='center', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 5: Optimized Structure
    box5 = FancyBboxPatch((8.5, 2.5), 1.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightcyan', edgecolor='black', linewidth=2)
    ax.add_patch(box5)
    ax.text(9.4, 2.9, 'Optimized\nStructure', ha='center', va='center', fontsize=11, fontweight='bold')
    
    # Arrow 5 (down)
    arrow5 = FancyArrowPatch((9.4, 2.5), (9.4, 1.7), 
                             arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
    ax.add_patch(arrow5)
    ax.text(9.7, 2.1, '5. MLIP\nRelaxation', ha='left', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    # Step 6: Final Structure
    box6 = FancyBboxPatch((7.5, 0.5), 3.8, 0.8, boxstyle="round,pad=0.1", 
                          facecolor='lightgreen', edgecolor='black', linewidth=2)
    ax.add_patch(box6)
    ax.text(9.4, 0.9, 'Final Relaxed Structure + Energy', ha='center', va='center', 
            fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'decoding_workflow.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated: {output_dir / 'decoding_workflow.png'}")

def plot_cycle_basis_explanation():
    """Illustrate cycle basis computation."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Cycle Basis Computation', fontsize=16, fontweight='bold')
    
    # Left: Graph with cycles
    ax = axes[0]
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0), (0, 2), (1, 3)])
    pos = nx.spring_layout(G, seed=42)
    
    # Draw graph
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color='lightblue', node_size=1000)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray', width=2)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12, font_weight='bold')
    
    # Highlight cycles
    cycle1 = [(0, 1), (1, 2), (2, 0)]
    cycle2 = [(0, 2), (2, 3), (3, 0)]
    cycle3 = [(1, 2), (2, 3), (3, 1)]
    
    nx.draw_networkx_edges(G, pos, edgelist=cycle1, ax=ax, edge_color='red', width=3, alpha=0.5)
    nx.draw_networkx_edges(G, pos, edgelist=cycle2, ax=ax, edge_color='blue', width=3, alpha=0.5)
    nx.draw_networkx_edges(G, pos, edgelist=cycle3, ax=ax, edge_color='green', width=3, alpha=0.5)
    
    ax.set_title('Graph with Multiple Cycles', fontweight='bold')
    ax.axis('off')
    
    # Right: Cycle basis
    ax = axes[1]
    ax.text(0.5, 0.9, 'Cycle Basis (Independent Cycles)', ha='center', 
            fontsize=14, fontweight='bold', transform=ax.transAxes)
    ax.text(0.1, 0.75, '1. Find Minimum Spanning Tree (MST)', 
            fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.15, 0.65, '   • Connects all nodes with minimum edges', 
            fontsize=10, transform=ax.transAxes)
    ax.text(0.15, 0.6, '   • |E₁| = number of edges in MST', 
            fontsize=10, transform=ax.transAxes)
    
    ax.text(0.1, 0.5, '2. Compute Homology Rank', 
            fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.15, 0.4, '   • H₁(X,ℤ) = |E| - |E₁|', 
            fontsize=10, family='monospace', transform=ax.transAxes)
    ax.text(0.15, 0.35, '   • Number of independent cycles', 
            fontsize=10, transform=ax.transAxes)
    
    ax.text(0.1, 0.25, '3. Extract Cycle Basis', 
            fontsize=12, fontweight='bold', transform=ax.transAxes)
    ax.text(0.15, 0.15, '   • Each cycle = edge not in MST', 
            fontsize=10, transform=ax.transAxes)
    ax.text(0.15, 0.1, '   • Forms basis for cycle space', 
            fontsize=10, transform=ax.transAxes)
    
    ax.text(0.5, 0.02, 'For 3D embedding: H₁(X,ℤ) ≥ 3 required', 
            ha='center', fontsize=11, fontweight='bold', color='green',
            transform=ax.transAxes)
    
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'cycle_basis.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated: {output_dir / 'cycle_basis.png'}")

if __name__ == "__main__":
    print("Generating SLICES documentation illustrations...")
    plot_strategy_comparison()
    plot_graph_topology_check()
    plot_encoding_workflow()
    plot_decoding_workflow()
    plot_cycle_basis_explanation()
    print(f"\n✓ All illustrations generated in {output_dir}/")

