import ase.io
import spglib
from quippy.potential import Potential
from ase import Atoms
from ase.phonons import Phonons as AsePhonons
import matplotlib.pyplot as plt
import numpy as np
import cellconstructor as CC
import cellconstructor.Structure
import cellconstructor.Phonons
import os

#GIVE THE TEST SET and the RESULTS DIR
gap_file='GAP/GAP.xml'
structure='../harmonic_ph/2x2x2/results_scf/CsV3Sb5.scf.pwo'
results_dir='harmonic_ph/2x2x2'
grid=[2,2,2]

isExist = os.path.exists(results_dir)
if not isExist:
    os.makedirs(results_dir)

print('Loading the potential...')
pot = Potential('IP GAP', param_filename=gap_file)
print()

atoms = ase.io.read(structure)
atoms.set_calculator(pot)

print('Running phonon calculation...')
ph = AsePhonons(atoms, pot, supercell=(grid[0], grid[1], grid[2]), delta=1e-3)
ph.run()
ph.read(acoustic=True)
ph.clean()
print()

print('Symmetryzing and saving...')
dyn=CC.Phonons.get_dyn_from_ase_phonons(ph)
dyn.Symmetrize()
dyn.save_qe(results_dir+'/gap.dyn')
