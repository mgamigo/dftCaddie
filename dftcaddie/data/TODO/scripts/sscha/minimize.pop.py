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
    return TEMP,meaningful_factor,minim_struc,min_step_struc,min_step_dyn,kong_liu_ratio

def last_population(folder_path='sscha/data_ensemble'):
    highest_x = 0
    # Iterate over the filenames in the folder
    for filename in os.listdir(folder_path):
        if filename.startswith('dyn_gen_pop'):
            parts = filename.strip('dyn_gen_pop').split('_')
            x_value = int(parts[0])
            if x_value > highest_x:
                highest_x = x_value
    return highest_x

#*****************************************************************************

# We setup an ensemble for the SSCHA at T = 0 K using the density matrix  from the dyn dynamical matrix
N_pop = last_population()
TEMP,meaningful_factor,minim_struc,min_step_struc,min_step_dyn,kong_liu_ratio = read_input('sscha.input')

print('\n\n**************')
print('Population =',N_pop)
print('Temperature =',TEMP)
print('meaningful_factor =',meaningful_factor)
print('minim_struc =',minim_struc)
print('min_step_struc =',min_step_struc)
print('min_step_dyn =',min_step_dyn)
print('kong_liu_ratio =',kong_liu_ratio)
print('\n**************')

#Load the dynamical matrices from the harmonic calculation or last population
if N_pop==1:
    NUM_dyn=len(glob.glob('sscha/start.dyn*'))
    file=os.listdir('sscha/')[1]
    dot_place=file.find(".")
    prefix=file[:5]
    dyn = CC.Phonons.Phonons("sscha/start.dyn", nqirr =NUM_dyn)
    dyn.Symmetrize()
    dyn.ForcePositiveDefinite()
    print("\nSTEP: Loading",NUM_dyn,"dynamical matrices from start.dyn ...")
else:
    name="dyn_end_population"+str(N_pop-1)
    list=os.listdir("sscha")
    NUM_dyn=sum(name in s for s in list)
    dyn = CC.Phonons.Phonons("sscha/"+name+"_", nqirr =NUM_dyn)
    print("\nSTEP: Loading",NUM_dyn,"dynamical matrices from the",N_pop-1,"population")

#Load ensemble
print('\nSTEP: Loading population',N_pop,'...')
ensemble = sscha.Ensemble.Ensemble(dyn, T0 = TEMP, supercell= dyn.GetSupercell())
ensemble.load_bin("sscha/data_ensemble", population_id = N_pop)

#MINIMIZATION***************************************
print('\nSTEP: Performing the minimization ...\n')
# Lets reset other calculation if you run this cell multiple times
ensemble.update_weights(dyn, TEMP) # Restore the original density matrix at T = # K
#Meaningfull factor ratio between gradient and error that considers whether the minimization is converged is 1 by default (1e-12 is a typical value)
minimizer = sscha.SchaMinimizer.SSCHA_Minimizer(ensemble,meaningful_factor=meaningful_factor)

#Ignore the structure minimization (I want the structure to be fixed)
minimizer.minim_struct = minim_struc
minimizer.min_step_struc=min_step_struc

# Setup the minimization parameter for the covariance matrix / OPTIMIZATION STEP
# If the minimization ends with few steps (less than 10), decrease it, if it takes too much, increase it
minimizer.min_step_dyn = min_step_dyn # Values around 1 are good
#minimizer.precond_dyn = False
#minimizer.root_representation = "root4"
# Setup the threshold for the ensemble wasting
minimizer.kong_liu_ratio = kong_liu_ratio # Usually 0.5 is a good value

# Lest start the minimization
minimizer.init()
freqs=[]
minimizer.run(custom_function_post = get_current_frequencies)
minimizer.finalize()

save_file_freqs(freqs)

#SAVE RESULTS***************************************
# We can save the dynamical matrix
minimizer.dyn.save_qe("sscha/dyn_end_population"+str(N_pop)+"_")

print('\n**************\n')
print('DONE')
