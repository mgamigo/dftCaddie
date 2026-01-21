#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks=96
#SBATCH --mem=180gb
#SBATCH --partition=intelnodes
#SBATCH --time=240:00:00
#SBATCH --job-name="NONAME"

export NPROCS=$SLURM_NTASKS
NPOOLS=`python -c "print($NPROCS / 4)"`
export $NPOOLS
cd $SLURM_SUBMIT_DIR

##########################################################################
module purge
#Load system
source SYSTEM.INFO

module load Intel/OneAPI_2021.2.0
module load Wannier90/Wannier90-3.1.0-Parallel
bash scf.sh
bash nscf.sh
bash wannier1.sh
bash wannier2.sh
bash wannier3.sh

#########################################################################

echo "DONE"
