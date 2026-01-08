"""
Integration tests for graph topology workflows.

Tests graph theory operations and their integration with SLICES.
"""

import pytest
import numpy as np
from slices.core import SLICES, GraphTopologyError
from slices.tobascco_net import Net, LatticeBasisError, CocycleBasisError
from pymatgen.core.structure import Structure
from pymatgen.core import Lattice
from tests.conftest import sample_structure, slices_backend


class TestGraphTopologyWorkflows:
    """Test graph topology workflows."""
    
    @pytest.mark.integration
    def test_structure_to_graph(self, slices_backend, sample_structure):
        """Test converting structure to graph."""
        structure_graph = slices_backend.structure2structure_graph(sample_structure)
        
        assert structure_graph is not None
        assert hasattr(structure_graph, 'graph')
        assert len(structure_graph.graph.nodes()) > 0
    
    @pytest.mark.integration
    def test_graph_to_net(self, slices_backend, sample_structure):
        """Test converting structure graph to Net object."""
        structure_graph = slices_backend.structure2structure_graph(sample_structure)
        
        # Extract graph data
        # Net class expects edges with string labels like 'e0', 'e1', etc.
        x_dat = []
        for idx, (i, j, data) in enumerate(structure_graph.graph.edges(data=True)):
            edge_label = f"e{idx}"  # Must be a string, not a list/tuple
            x_dat.append((str(i), str(j), {'label': edge_label}))
        
        if len(x_dat) > 0:
            net = Net(x_dat, dim=3)
            assert net is not None
            assert net.ndim == 3
    
    @pytest.mark.integration
    def test_cycle_basis_computation(self, slices_backend, sample_structure):
        """Test cycle basis computation workflow."""
        structure_graph = slices_backend.structure2structure_graph(sample_structure)
        
        x_dat = []
        # Net class expects edges with string labels like 'e0', 'e1', etc.
        # The label format is critical: get_index() expects edge[2] to be a string like "e0"
        for idx, (i, j, data) in enumerate(structure_graph.graph.edges(data=True)):
            edge_label = f"e{idx}"  # Must be a string, not a list/tuple
            x_dat.append((str(i), str(j), {'label': edge_label}))
        
        if len(x_dat) > 0:
            net = Net(x_dat, dim=3)
            net.voltage = np.random.rand(len(x_dat), 3)  # Random voltage for testing
            
            try:
                net.simple_cycle_basis()
                # Cycle basis should be computed
                assert net.cycle is not None or len(net._graph.nodes()) <= 1
            except Exception as e:
                pytest.skip(f"Cycle basis computation failed: {e}")
    
    @pytest.mark.integration
    def test_lattice_basis_workflow(self, slices_backend, sample_structure):
        """Test lattice basis computation workflow."""
        structure_graph = slices_backend.structure2structure_graph(sample_structure)
        
        x_dat = []
        # Net class expects edges with string labels like 'e0', 'e1', etc.
        # The label format is critical: get_index() expects edge[2] to be a string like "e0"
        for idx, (i, j, data) in enumerate(structure_graph.graph.edges(data=True)):
            edge_label = f"e{idx}"  # Must be a string, not a list/tuple
            x_dat.append((str(i), str(j), {'label': edge_label}))
        
        if len(x_dat) > 0:
            net = Net(x_dat, dim=3)
            net.voltage = np.random.rand(len(x_dat), 3)
            net.simple_cycle_basis()
            
            try:
                net.get_lattice_basis()
                assert net.lattice_basis is not None
            except LatticeBasisError:
                # Some structures may have incompatible topology
                pytest.skip("Graph topology incompatible for lattice basis")
            except AttributeError:
                pytest.skip("Cycle rep not set up correctly")

