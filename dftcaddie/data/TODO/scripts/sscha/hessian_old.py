from __future__ import print_function
from __future__ import division
import sys,os
import shutil
import subprocess
import glob

import numpy as np
import matplotlib.pyplot as plt

from ase.visualize import view

# We import the basis modules for the SSCHA
import cellconstructor as CC
import cellconstructor.Structure
import cellconstructor.Phonons

# Import the SSCHA engine (we will use it later)
import sscha, sscha.Ensemble, sscha.SchaMinimizer, sscha.Relax

def maxpop(list):
    #returns the las population integer
    maxpop=1
    for s in list:
        if ("dyn_start_population" in s):
            pop=int(s[20:].split('_')[0])
            if (pop>maxpop):
                maxpop=pop
    return maxpop

def num_configs(population):
    #returns the number of configs for a given population
    list=glob.glob("sscha/data_ensemble/scf_population"+str(population)+"_*")
    configs=len(list)
    return configs

def hessian_evolution(min_configs,max_configs,step,population,nqirr,temp,save_as=None):
    f = open("OUTPUT.txt", "w")
    f.write("EVOLUTION OF THE HESSIAN"+"\n")
    f.close()
    dyn = CC.Phonons.Phonons("sscha/dyn_end_population"+str(population)+"_", nqirr)
    results = []
    for configs in range(min_configs,max_configs+step,step):
        f = open("OUTPUT.txt", "a")
        f.write("computing hessian with "+str(configs)+" configurations..."+"\n")
        f.close()
        ensemble = sscha.Ensemble.Ensemble(dyn, T0 = temp, supercell= dyn.GetSupercell())
        ensemble.load("sscha/data_ensemble", population = population, N = configs)
        ensemble.update_weights(dyn,temp)
        dyn_hessian = ensemble.get_free_energy_hessian(include_v4 = True)
        w_hessian, pols_hessian = dyn_hessian.DiagonalizeSupercell()
        freq=w_hessian*CC.Units.RY_TO_CM
        freq=np.insert(freq,0,configs)
        results.append(freq)
    results=np.stack(results, axis=0)
    np.savetxt('hessian_evo_v4.dat',results)
    plt.figure()
    plt.plot(results[:,0], results[:,1:], '.-', label='line 1', linewidth=1)
    plt.ylabel("frequencies [cm-1]")
    plt.xlabel("Number of configs")
    if save_as!=None:
        plt.savefig(save_as,dpi=300)

print("THE JOB STARTS HERE*************")

#TEMPERATURE*******************************
T=0

#**********************************************************************************************
#HESSIAN EVOLUTION AS YOU ADD CONFIGS

files=os.listdir("sscha")
population=maxpop(files)
configs=num_configs(population)
name="dyn_end_population"+str(population)
num_q=sum(name in s for s in files)

s=["population", population,", max configs", configs, ", Num_q", num_q, ", temperature",T,"K"]
f = open("OUTPUT.txt", "a")
f.write(' '.join(map(str, s))+'\n')
f.write("Computing hessian evolution with v4...")
f.close()

hessian_evolution(100,configs,50,population,num_q,T,save_as="hessian_evo.png")
        
f = open("OUTPUT.txt", "a")
f.write("Done!")
f.close()

#**********************************************************************************************
#COMPUTE HESSIAN WITH V4 WITH ALL CONFIGS


files=os.listdir("sscha")
population=maxpop(files)
configs=num_configs(population)
name="dyn_end_population"+str(population)
num_q=sum(name in s for s in files)

s=["population", population,", max configs", configs, ", Num_q", num_q, ", temperature",T,"K"]
f = open("OUTPUT.txt", "a")
f.write(' '.join(map(str, s))+'\n')
f.write("Computing hessian with v4 term and all the configs...")
f.close()

#Load the ensable with the new collected data
dyn = CC.Phonons.Phonons("sscha/dyn_end_population"+str(population)+"_", nqirr =num_q)

ensemble = sscha.Ensemble.Ensemble(dyn, T0 = T, supercell= dyn.GetSupercell())
ensemble.load("sscha/data_ensemble", population = population, N = configs)
ensemble.update_weights(dyn,T)

dyn_hessian = ensemble.get_free_energy_hessian(include_v4 = True) # We neglect high-order four phonon scattering

# We can save it
if os.path.exists("hessian_v4"):
    shutil.rmtree("hessian_v4")
os.mkdir("hessian_v4")
dyn_hessian.save_qe("hessian_v4/hessian")
