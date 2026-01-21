from __future__ import print_function
from __future__ import division

import numpy as np
import sys,os,re
import shutil
import subprocess
import glob

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
def read_input(file):
    lines = open(file,'r')
    for line in lines:
        if re.search('temperature',line):
            TEMP=int(line.split('#')[0].split('=')[1])
        if re.search('gap_file',line):
            gap_file=line.split('#')[0].split('=')[1].strip()
        if re.search('pop_configs',line):
            pop_configs=int(line.split('#')[0].split('=')[1])
    return TEMP, gap_file, pop_configs

def last_population(folder_path='sscha'):
    highest_x = 0
    # Iterate over the filenames in the folder
    for filename in os.listdir(folder_path):
        if filename.startswith('dyn_end_population'):
            parts = filename.strip('dyn_end_population').split('_')
            x_value = int(parts[0])
            if x_value > highest_x:
                highest_x = x_value
    return highest_x
    
#*****************************************************************************

TEMP, gap_file, pop_configs = read_input('sscha.input')
N_pop=last_population()+1

print('\n**************')
print('Population =',N_pop)
print('Temperature =',TEMP)
print('pop_configs=',pop_configs)
print('gap_file =',gap_file)
print('\n**************\n\n')

#Check whether the population exists
if not os.path.exists("sscha"):
    os.mkdir("sscha")
    files=glob.glob('harmonic/results_ph/*dyn*')
    for file in files:
        dyn=file.split('.')[1]
        if dyn!='dyn0':
            shutil.copyfile(file, 'sscha/start.'+dyn)

#Load the dynamical matrices from the harmonic calculation or last population
if N_pop==1:
    NUM_dyn=len(glob.glob('sscha/start.dyn*'))
    file=os.listdir('sscha/')[1]
    dot_place=file.find(".")
    prefix=file[:5]
    dyn = CC.Phonons.Phonons("sscha/start.dyn", nqirr =NUM_dyn)
#    dyn.save_qe('sscha/dyn_start_population'+str(N_pop)+'_')
    dyn.Symmetrize()
    dyn.ForcePositiveDefinite()
    print("\nSTEP: Loading",NUM_dyn,"dynamical matrices from start.dyn ...")
else:
    name="dyn_end_population"+str(N_pop-1)
    list=os.listdir("sscha")
    NUM_dyn=sum(name in s for s in list)
    dyn = CC.Phonons.Phonons("sscha/"+name+"_", nqirr =NUM_dyn)
    print("\nSTEP: Loading",NUM_dyn,"dynamical matrices from the",N_pop-1,"population")

#Create ensemble
print('\nSTEP: Creating ensemble with',pop_configs,'configs ...')
ensemble = sscha.Ensemble.Ensemble(dyn, T0 = TEMP, supercell= dyn.GetSupercell())
ensemble.generate(N = pop_configs)

#Compute ensemble
print('\nSTEP: Loading GAP potential ...')
pot = Potential('IP GAP', param_filename=gap_file)
print('\nSTEP: Computing ensemble using GAP ...')
ensemble.compute_ensemble(pot)
print('\nSTEP: Saving ensemble ...')
ensemble.save_bin('sscha/data_ensemble',population_id=N_pop)

print('\n**************\n')
print('DONE')
