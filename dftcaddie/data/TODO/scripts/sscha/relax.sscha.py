from __future__ import print_function
from __future__ import division

import numpy as np
import sys,os
import shutil
import subprocess
import glob
import re

# We import the basis modules for the SSCHA
import cellconstructor as CC
import cellconstructor.Structure
import cellconstructor.Phonons

# Import the SSCHA engine (we will use it later)
import sscha, sscha.Ensemble, sscha.SchaMinimizer, sscha.Relax

# For the GAP ML potential
from quippy.potential import Potential
from ase import Atoms
from ase.phonons import Phonons as AsePhonons
from ase.constraints import ExpCellFilter
from ase.optimize import QuasiNewton

#Necesssary functions
def get_current_frequencies(minimizer):
    curr_freqs,_ = minimizer.dyn.DiagonalizeSupercell()
    freqs.append(curr_freqs)

def save_file_freqs(freqs):
    print('\n \n')
    print('***********\n')
    print('Frequencies\n')
    print('***********\n')
    np.savetxt(sys.stdout,freqs)

def read_input(file):
    lines = open(file,'r')
    for line in lines:
        if re.search('temperature',line):
            TEMP=int(line.split('#')[0].split('=')[1])
        if re.search('meaningful_factor',line):
            meaningful_factor=float(line.split('#')[0].split('=')[1])
        if re.search('minim_struc',line):
            minim_struc=('True' in line.split('#')[0].split('=')[1])
        if re.search('min_step_struc',line):
            min_step_struc=float(line.split('#')[0].split('=')[1])
        if re.search('min_step_dyn',line):
            min_step_dyn=float(line.split('#')[0].split('=')[1])
        if re.search('kong_liu_ratio',line):
            kong_liu_ratio=float(line.split('#')[0].split('=')[1])
        if re.search('gap_file',line):
            gap_file=line.split('#')[0].split('=')[1].strip()
        if re.search('relax_configs',line):
            relax_configs=int(line.split('#')[0].split('=')[1])
        if re.search('max_pop',line):
            max_pop=int(line.split('#')[0].split('=')[1])
        if re.search('max_steps',line):
            max_steps=int(line.split('#')[0].split('=')[1])
    return TEMP,meaningful_factor,minim_struc,min_step_struc,min_step_dyn,kong_liu_ratio,\
            gap_file,relax_configs,max_pop,max_steps

#*****************************************************************************

# RELAX WITH SSCHA
TEMP,meaningful_factor,minim_struc,min_step_struc,min_step_dyn,kong_liu_ratio,\
gap_file,relax_configs,max_pop,max_steps = read_input('sscha.input')

print('\n\n**************')
print('Temperature =',TEMP)
print('meaningful_factor =',meaningful_factor)
print('minim_struc =',minim_struc)
print('min_step_struc =',min_step_struc)
print('min_step_dyn =',min_step_dyn)
print('kong_liu_ratio =',kong_liu_ratio)
print('relax_configs =',relax_configs)
print('max_pop =',max_pop)
print('max_steps =',max_steps)
print('gap_file =',gap_file)
print('\n**************\n\n')

# Read in the GAP potential 
pot = Potential('IP GAP', param_filename=str(gap_file))

# Load the dynamical matrices of the supercell for calculation of force constants
nqirr=len(glob.glob('sscha/start.dyn*'))
dyn = CC.Phonons.Phonons('sscha/start.dyn', nqirr)
dyn.Symmetrize()
dyn.ForcePositiveDefinite()

# Generate the ensemble and the minimizer objects
ensemble = sscha.Ensemble.Ensemble(dyn, T0=TEMP, supercell = dyn.GetSupercell())
ensemble.generate(N = relax_configs)
minimizer = sscha.SchaMinimizer.SSCHA_Minimizer(ensemble)

# We setup all the minimization parameters
minimizer.minim_struct = minim_struc
minimizer.min_step_struc=min_step_struc
minimizer.min_step_dyn = min_step_dyn
minimizer.kong_liu_ratio = kong_liu_ratio
minimizer.meaningful_factor = meaningful_factor
minimizer.max_ka = max_steps  #Maximum number of SSCHA steps

# First relax in quantum limit for fixed cell
freqs=[]
relax = sscha.Relax.SSCHA(minimizer, ase_calculator = pot, N_configs = relax_configs, max_pop = max_pop,save_ensemble = True)
relax.setup_custom_functions(custom_function_post = get_current_frequencies)
relax.relax(ensemble_loc='sscha/data_ensemble')
save_file_freqs(freqs)
print('\n**************\n')

pop=str(relax.minim.population)
relax.minim.dyn.save_qe('dyn_pop'+pop+'_')
relax.minim.plot_results(save_filename = 'sscha/relax_sscha.txt', plot = False)

# Iterate over the files and move those starting with "dyn_pop" to the target directory
for file in os.listdir('./'):
    if file.startswith('dyn_pop'):
        tail=file.strip('dyn_pop')
        shutil.move(file, 'sscha/dyn_end_population'+tail)
