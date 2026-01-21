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
    read_kpoints=False
    fc3_grid=None
    for line in lines:
        if re.search('temperature',line):
            TEMP=int(line.split('#')[0].split('=')[1])
        if re.search('include_v4',line):
            include_v4=('True' in line.split('#')[0].split('=')[1])
        if re.search('static_limit',line):
            static_limit=('True' in line.split('#')[0].split('=')[1])
        if re.search('no_mode_mixing',line):
            nmm=('True' in line.split('#')[0].split('=')[1])
        if re.search('KGRID',line):
            kgrid=[int(x) for x in line.split('#')[0].split('=')[1].split()]
        if re.search('FC3_GRID',line):
            fc3_grid=[int(x) for x in line.split('#')[0].split('=')[1].split()]
        if re.search('#END_POINTS',line):
            read_kpoints=False
        if read_kpoints==True:
            p=np.array([float(x) for x in line.split('#')[0].split()])
            try:
                points=np.vstack((points,p))
            except NameError:
                points=p
        if re.search('#POINTS',line):
            read_kpoints=True
        if re.search('hessian_configs',line):
            try:
                hessian_configs=int(line.split('#')[0].split('=')[1])
            except IndexError:
                hessian_configs=0
    return TEMP,include_v4,hessian_configs,kgrid,fc3_grid,points,static_limit,nmm

#*****************************************************************************
#READ INPUT

TEMP,include_v4,hessian_configs,kgrid,fc3_grid,points,static_limit,nmm = read_input('sscha.input')

files=os.listdir("sscha")
N_pop=maxpop(files)

print('\n\n**************')
print('Population =',N_pop)
print('Temperature =',TEMP)
print('include_v4 =',include_v4)
print('KGRID =',kgrid)
if fc3_grid!=None:
    print('FC3_GRID =',fc3_grid)
print('Static limit =',static_limit)
print('No mode mixing =',nmm)
print('K points =')
print(points)
if hessian_configs != 0:
    print('hessian_configs =',hessian_configs)
print('\n**************')

#*****************************************************************************
#GET Spectral function

f = open("OUTPUT.txt", "a")
f.write("Computing the spectral function...")
f.close()
name="dyn_end_population"+str(N_pop)
num_q=sum(name in s for s in files)
#Load the ensable with the new collected data
dyn = CC.Phonons.Phonons("sscha/dyn_end_population"+str(N_pop)+"_", nqirr =num_q)
if fc3_grid!=None:
    supercell = fc3_grid
else:
    supercell = dyn.GetSupercell()
tensor3 = CC.ForceTensor.Tensor3(dyn.structure,dyn.structure.generate_supercell(supercell),supercell)
# Load tensor3
tensor3.SetupFromFile(fname="FC3/FC3",file_format='D3Q')
#Points in 2pi/Anstrom units
points=points/np.linalg.norm(dyn.structure.unit_cell[0])
if not os.path.exists('spectralF'):
    os.mkdir('spectralF')
if nmm==True:
    filename='spectralF/no_mixing'
elif static_limit==True:
    filename='spectralF/static' 
else:
    filename='spectralF/dynamic'
if nmm == False:
    CC.Spectral.get_full_dynamic_correction_along_path(dyn=dyn, 
                                                   tensor3=tensor3, 
                                                   k_grid=kgrid,
                                                   e1=300, de=0.1, e0=0, # energy grid
                                                   sm1=1.0, sm0=1.0,     # smearing values
                                                   sm1_id=0.1, sm0_id=0.1,
                                                   nsm=1,
                                                   T=TEMP,
                                                   q_path=points,
                                                   static_limit = static_limit,  # Static Approx
                                                   notransl = True,  # projects out the acoustic zone center modes
                                                   filename_sp=filename)
else:
    CC.Spectral.get_diag_dynamic_correction_along_path(dyn=dyn, 
                                                   tensor3=tensor3, 
                                                   k_grid=kgrid,
                                                   e1=300, de=0.1, e0=0, # energy grid
                                                   sm1=1.0, sm0=1.0,     # smearing values
                                                   sm1_id=0.1, sm0_id=0.1,
                                                   nsm=1,
                                                   T=TEMP,
                                                   q_path=points,
                                                   filename_sp=filename)
    files=glob.glob('./freq_dynamic*')+glob.glob('./v2_freq_shift*')+glob.glob('./db_new*')
    for file in files:
        shutil.move(file,'spectralF/'+file)

os.remove('path_len.dat')
f = open("OUTPUT.txt", "a")
f.write("Done!")
f.close()
