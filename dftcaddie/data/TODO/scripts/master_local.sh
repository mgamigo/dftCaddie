#!/bin/bash

#SBATCH --ntasks=1
#SBATCH --mem=1gb
#SBATCH -N 1
#SBATCH --time=47:59:00
#SBATCH --job-name="template"

#IF PARALELIZING PHONONS
#cp -r ../../../tmp ./

#copies the directory from where you submited the job to lscratch

##########################################################################
module purge
#QE
#module load intel/2019a
#module load intel/2021a
#WANNIER 90
#module load foss/2018b

#Load system
source SYSTEM.INFO

echo "put your jobs here"

#########################################################################

echo "DONE"
