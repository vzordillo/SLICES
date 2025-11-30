# MLIP Relaxer API Documentation

## MLIPRelaxer Interface

Abstract base class for MLIP (Machine Learning Interatomic Potential) model adapters.

### Factory Function

#### `get_relaxer(model_name, optimizer="BFGS")`

Create a relaxer instance for the specified MLIP model.

**Parameters:**
- `model_name` (str): Model name ('m3gnet', 'chgnet', 'matgl', 'mattersim', 'orbv3')
- `optimizer` (str): Optimizer ('BFGS', 'FIRE')

**Returns:**
- `MLIPRelaxer`: Relaxer instance

**Raises:**
- `ValueError`: If model name is invalid

### Relaxer Methods

#### `relax(structure, fmax=0.2, steps=100)`

Relax a crystal structure using the MLIP model.

**Parameters:**
- `structure` (Structure): pymatgen Structure to relax
- `fmax` (float): Maximum force convergence criterion
- `steps` (int): Maximum optimization steps

**Returns:**
- `tuple`: (relaxed_structure, energy_per_atom)

### Available Relaxers

- `M3GNetRelaxer`: Materials Project M3GNet model
- `CHGNetRelaxer`: Charge-informed GNN model
- `MatGLRelaxer`: Materials Project MatGL model
- `MatterSimRelaxer`: Microsoft MatterSim model
- `ORBv3Relaxer`: Orbital Materials ORBv3 model

