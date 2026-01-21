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
        if re.search('hessian_evo',line):
            hessian_evo=('True' in line.split('#')[0].split('=')[1])

        if re.search('min_configs',line):
            min_configs=int(line.split('#')[0].split('=')[1])
        if re.search('max_configs',line):
            max_configs=int(line.split('#')[0].split('=')[1])
        if re.search('step_configs',line):
            step_configs=int(line.split('#')[0].split('=')[1])
        if re.search('hessian_configs',line):
            try:
                hessian_configs=int(line.split('#')[0].split('=')[1])
            except IndexError:
                hessian_configs=0
    return TEMP,include_v4,hessian_evo,min_configs,max_configs,step_configs,hessian_configs

def hessian_evolution(ensemble,min_configs,max_configs,step,population,nqirr,temp,include_v4=True):
    f = open("OUTPUT.txt", "w")
    f.write("EVOLUTION OF THE HESSIAN"+"\n")
    f.close()
    dyn_end = CC.Phonons.Phonons("sscha/dyn_end_population"+str(N_pop)+"_", nqirr =nqirr)
    results = []
    for configs in range(min_configs,max_configs+step,step):
        selection=np.array([True]*configs+[False]*(ensemble.N-configs),dtype=bool)
        tmp_ensemble = ensemble.split(selection)
        tmp_ensemble.update_weights(dyn_end,temp)
        f = open("OUTPUT.txt", "a")
        f.write("computing hessian with "+str(tmp_ensemble.N)+" configurations..."+"\n")
        f.close()
        dyn_hessian = tmp_ensemble.get_free_energy_hessian(include_v4 = include_v4)
        w_hessian, pols_hessian = dyn_hessian.DiagonalizeSupercell()
        freq=w_hessian*CC.Units.RY_TO_CM
        freq=np.insert(freq,0,configs)
        results.append(freq)
    results=np.stack(results, axis=0)
    if include_v4==True:
        np.savetxt('hessian_evo_v4.dat',results)
    else:
        np.savetxt('hessian_evo_v3.dat',results)

#*****************************************************************************
#COMPUTE HESSIAN WITH V4 WITH ALL CONFIGS

TEMP,include_v4,hessian_evo,min_configs,max_configs,step_configs,hessian_configs = read_input('sscha.input')
files=os.listdir("sscha")
N_pop=maxpop(files)

print('\n\n**************')
print('Population =',N_pop)
print('Temperature =',TEMP)
print('include_v4 =',include_v4)
print('hessian_evo =',hessian_evo)
if hessian_evo==True:
    print('min_configs =',min_configs)
    print('max_configs =',max_configs)
    print('step_configs =',step_configs)
elif hessian_configs != 0:
    print('hessian_configs =',hessian_configs)
print('\n**************')


name="dyn_end_population"+str(N_pop)
num_q=sum(name in s for s in files)
#Load the ensable with the new collected data
dyn_end = CC.Phonons.Phonons("sscha/dyn_end_population"+str(N_pop)+"_", nqirr =num_q)
dyn_start = CC.Phonons.Phonons("sscha/data_ensemble/dyn_gen_pop"+str(N_pop)+"_", nqirr =num_q)
ensemble = sscha.Ensemble.Ensemble(dyn_start, T0 = TEMP, supercell= dyn_start.GetSupercell())
ensemble.load_bin("sscha/data_ensemble", population_id = N_pop)
configs=ensemble.N

if hessian_evo==False:
    if hessian_configs != 0:
        selection=np.array([True]*hessian_configs+[False]*(configs-hessian_configs),dtype=bool)
        ensemble = ensemble.split(selection)
        ensemble.update_weights(dyn_end,TEMP)
    ensemble.update_weights(dyn_end,TEMP)
    s=["population", N_pop,", max configs", configs, ", Num_q", num_q, ", temperature",TEMP,"K",", v4 =",include_v4]
    f = open("OUTPUT.txt", "a")
    f.write(' '.join(map(str, s))+'\n')
    f.write("Computing hessian with all the configs...")
    f.close()
    
    dyn_hessian = ensemble.get_free_energy_hessian(include_v4 = include_v4)
    
    # We can save it
    if include_v4==True:
        folder='hessian_v4'
    else:
        folder='hessian_v3'
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.mkdir(folder)
    dyn_hessian.save_qe(folder+"/hessian.dyn")

if hessian_evo==True:
    s=["population", N_pop,", max configs", configs, ", Num_q", num_q, ", temperature",TEMP,"K",", v4 =",include_v4]
    f = open("OUTPUT.txt", "a")
    f.write(' '.join(map(str, s))+'\n')
    f.write("Computing hessian evolution as function of configs ...")
    f.close()
    
    hessian_evolution(ensemble,min_configs,max_configs,step_configs,N_pop,num_q,TEMP,include_v4=include_v4)
            
f = open("OUTPUT.txt", "a")
f.write("Done!")
f.close()
