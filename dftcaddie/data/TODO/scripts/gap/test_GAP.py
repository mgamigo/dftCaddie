import numpy as np
import ase
from quippy.potential import Potential
from ase import Atoms
import time
import matplotlib.pyplot as plt
import os

#GIVE THE TEST SET, GAP POTENTIAL and RESULTS DIR
infile = 'sets/test.xyz' 
gap_file = 'GAP/GAP.xml'
results_dir='test_GAP/'
atoms = ase.io.read(infile, ':')    # Read in .xyz files using ase method

#BASIC Properties of the TEST SET
nconf = len(atoms)
natoms = [len(at.symbols) for at in atoms]
volume = [atom.get_volume()/float(len(atom.get_scaled_positions())) for atom in atoms]
print('Number of configurations in the dataset: ' + str(nconf), flush = True)
print('Number of atoms per configuration: ' + str(natoms[0]), flush = True)
print('Average volume: ', np.mean(volume))

#LOAD THE GAP MACHINE LEARNING POTENTIAL
pot = Potential('IP GAP', param_filename=gap_file, calc_args='local_gap_variance') # Read in potential

#OBTAIN energies, forces, stress, variance and volumes with GAP
en_gap = []
forces_gap = []
stress_gap = []
var_gap = []
volume = []
for i in range(nconf):
    #if(i%100 == 0):
    print('Configuration: ', i + 1)
    atoms_gap = Atoms(symbols = atoms[i].symbols, cell = atoms[i].cell,\
    scaled_positions = atoms[i].get_scaled_positions(), calculator = pot, pbc = True)
    en_gap.append(atoms_gap.get_potential_energy()) # Calculate total energies of structures with GAP
    forces_gap.append(atoms_gap.get_forces()) # Calculate forces on atoms
    stress_gap.append(atoms_gap.get_stress()) # Calculate forces on atoms
    extra_results = atoms_gap.calc.extra_results
    var_gap.append(np.average(extra_results['atoms']['local_gap_variance']))
    volume.append(atoms_gap.get_volume())

#GET THE ERRORS respect to the DFT results
energy_errors = np.zeros_like(en_gap)
forces_error = np.zeros_like(forces_gap)
stress_error = np.zeros_like(stress_gap)
for i in range(nconf):
    energy_errors[i] = (atoms[i].get_potential_energy() - en_gap[i])/natoms[i] # Calculate energy errors
    forces_error[i] = atoms[i].get_forces() - forces_gap[i]    # Calculate errors on forces
    stress_error[i] = atoms[i].get_stress() - stress_gap[i]    # Calculate errors on forces


# WRITE ERRORS
isExist = os.path.exists(results_dir)
if not isExist:
    os.makedirs(results_dir)
    
with open(results_dir+'energy', 'w+') as outfile:
    outfile.write('#[energy/atom, GAP_energy/atom, error/atom, local_gap_variance] (for each config) (eV) \n')
    for i in range(nconf):
        outfile.write(4*' ' + format(atoms[i].get_potential_energy()/natoms[i], '.10e'))
        outfile.write(4*' ' + format(en_gap[i]/natoms[i], '.10e'))
        outfile.write(4*' ' + format(energy_errors[i], '.10e'))
        outfile.write(4*' ' + format(var_gap[i], '.10e'))
        outfile.write('\n')

with open(results_dir+'forces', 'w+') as outfile:    # Output errors by Cartesian coordinate
    outfile.write('#[forces_i, forces_gap_i, forces_error_i] x 3 with (i=x,y,z) (for each atom in each config) (eV/ang) \n')
    for i in range(nconf):
        for j in range(natoms[i]):
            for k in range(3):
                outfile.write(4*' ' + format(atoms[i].get_forces()[j][k], '.12f'))
                outfile.write(4*' ' + format(forces_gap[i][j][k], '.12f'))
                outfile.write(4*' ' + format(forces_error[i][j][k], '.12f'))
            outfile.write('\n')

with open(results_dir+'stress', 'w+') as outfile:    # Output errors by Cartesian coordinate
    outfile.write('#[stress_i, stress_gap_i, error_i] (with i=xx,yy,zz,yz,xz,xy) (for each config) (eV/ang^3) \n')
    for i in range(nconf):
        for k in range(6):
            outfile.write(4*' ' + format(atoms[i].get_stress()[k], '.12f'))
            outfile.write(4*' ' + format(stress_gap[i][k], '.12f'))
            outfile.write(4*' ' + format(stress_error[i][k], '.12f'))
        outfile.write('\n')
