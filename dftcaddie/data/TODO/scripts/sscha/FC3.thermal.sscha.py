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
import cellconstructor.ForceTensor
import cellconstructor.Spectral
import cellconstructor.ThermalConductivity

# Import the SSCHA engine (we will use it later)
import sscha, sscha.Ensemble, sscha.SchaMinimizer, sscha.Relax

#Necesssary functions

def maxpop(list):
    #returns the las population integer
    maxpop=1
    for s in list:
        if ("dyn_end_population" in s):
            pop=int(s[18:].split('_')[0])
            if (pop>maxpop):
                maxpop=pop
    return maxpop

def read_input(file):
    hessian_configs=0
    lines = open(file,'r')
    for line in lines:
        if re.search('temperature',line):
            TEMP=int(line.split('#')[0].split('=')[1])
        if re.search('include_v4',line):
            include_v4=('True' in line.split('#')[0].split('=')[1])
        if re.search('hessian_configs',line):
            try:
                hessian_configs=int(line.split('#')[0].split('=')[1])
            except IndexError:
                hessian_configs=0
    return TEMP,include_v4,hessian_configs

#*****************************************************************************
#READ INPUT
TEMP,include_v4,hessian_configs = read_input('sscha.input')

files=os.listdir("sscha")
N_pop=maxpop(files)

print('\n\n**************')
print('Population =',N_pop)
print('Temperature =',TEMP)
print('include_v4 =',include_v4)
if hessian_configs != 0:
    print('hessian_configs =',hessian_configs)
print('\n**************')


#*****************************************************************************
#Compute hessian

name="dyn_end_population"+str(N_pop)
num_q=sum(name in s for s in files)
#Load the ensable with the new collected data
dyn_start = CC.Phonons.Phonons("sscha/data_ensemble/dyn_gen_pop"+str(N_pop)+"_", nqirr =num_q)
dyn_end = CC.Phonons.Phonons("sscha/dyn_end_population"+str(N_pop)+"_", nqirr =num_q)
ensemble = sscha.Ensemble.Ensemble(dyn_start, T0 = TEMP, supercell= dyn_start.GetSupercell())
ensemble.load_bin("sscha/data_ensemble", population_id = N_pop)
configs=ensemble.N

if hessian_configs != 0:
    selection=np.array([True]*hessian_configs+[False]*(configs-hessian_configs),dtype=bool)
    ensemble = ensemble.split(selection)
else:
    hessian_configs=configs
ensemble.update_weights(dyn_end,TEMP)
s=["population", N_pop,", max configs", configs, ", Num_q", num_q, ", temperature",TEMP,"K",", v4 =",include_v4]
f = open("OUTPUT.txt", "a")
f.write(' '.join(map(str, s))+'\n')
f.write("Computing hessian with "+str(hessian_configs)+ " configs... \n")
f.close()

dyn_hessian = ensemble.get_free_energy_hessian(include_v4=include_v4,get_full_hessian=True,verbose=True)

# We can save it
if include_v4==True:
    folder='hessian_v4'
else:
    folder='hessian_v3'
if os.path.exists(folder):
    shutil.rmtree(folder)
if not os.path.exists('FC3'):
    os.mkdir('FC3')
os.mkdir(folder)
dyn_hessian.save_qe(folder+"/hessian.dyn")
shutil.move('d3_realspace_nosym.npy','FC3/d3_realspace_nosym.npy')
shutil.move('d3_realspace_sym.npy','FC3/d3_realspace_sym.npy')
shutil.move('phi_odd.npy','FC3/phi_odd.npy')
#shutil.move('SupercellOddDynHa1','FC3/SupercellOddDynHa1')
