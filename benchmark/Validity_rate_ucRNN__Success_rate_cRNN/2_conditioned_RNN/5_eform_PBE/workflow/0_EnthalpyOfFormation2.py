# -*- coding: utf-8 -*-
"""
Created on Wed Dec 19 18:47:34 2018
Read structure files and automatically calculate formation enthalpy.
@author: xiaoh
"""
import json
from pymatgen.core.structure import Structure
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.apps.borg.hive import VaspToComputedEntryDrone
from pymatgen.apps.borg.queen import BorgQueen
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
from pymatgen.entries.compatibility import MaterialsProjectCompatibility
from pymatgen.core.composition import Composition
from pymatgen.core.periodic_table import Element
#from pymatgen.ext.matproj import MPRester
# Load chemical potential database
#a = MPRester("PWvnIjizov7K5a3nLw6y")


with open('./chemPotMP.json') as handle:
    chemPot = json.loads(handle.read())
# Load calculation results
drone = VaspToComputedEntryDrone()
queen = BorgQueen(drone, "EFormation", 1)
entries = queen.get_data()
# Apply compatibility corrections and calculate formation enthalpy
compat = MaterialsProjectCompatibility()
compat.process_entries(entries)
entry = entries[0]
enthalpyForm=entry.energy
temp=entry.composition.get_el_amt_dict()
for i in range(len(temp)):
    enthalpyForm=enthalpyForm-list(temp.values())[i]*chemPot[list(temp.keys())[i]]
enthalpyForm=enthalpyForm/entry.composition.num_atoms
f = open("results.txt", "w")
f.write(str(enthalpyForm))

