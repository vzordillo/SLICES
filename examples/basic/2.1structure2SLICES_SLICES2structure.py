import os
os.environ["CUDA_VISIBLE_DEVICES"]=""
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load crystal structure
original_structure = Structure.from_file(filename='NdSiRu.cif')

# Initialize SLICES with MLIP model for relaxation
# Supported models: 'm3gnet' (default), 'chgnet', 'mattersim', 'orbv3'
# Example: Using M3GNet (default)
backend = SLICES(relax_model="m3gnet")

# Alternative options:
# backend = SLICES()                       # Defaults to m3gnet
# backend = SLICES(relax_model="chgnet")  # CHGNet model
# backend = SLICES(relax_model="mattersim")  # MatterSim model
# backend = SLICES(relax_model="orbv3")   # ORBv3 model

# Convert crystal structure to SLICES string
slices_NdSiRu = backend.structure2SLICES(original_structure) 

# Reconstruct crystal structure from SLICES string and get MLIP-predicted energy
reconstructed_structure, final_energy_per_atom_IAP = backend.SLICES2structure(slices_NdSiRu)

print('SLICES string of NdSiRu is: ', slices_NdSiRu)
print('\nOriginal structure is: ', original_structure)
print('\nReconstructed structure is: ', reconstructed_structure)
print('\nFinal energy per atom (MLIP): ', final_energy_per_atom_IAP, ' eV/atom')

# Note: If final_energy_per_atom_IAP is 0, it means the MLIP relaxation failed,
# and the reconstructed_structure is the ZL*-optimized structure.

