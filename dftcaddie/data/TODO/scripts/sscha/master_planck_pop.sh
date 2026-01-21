#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=48
#SBATCH --time=120:00:00
#SBATCH --partition=intelnodes
#SBATCH --mem=92gb
#SBATCH --job-name="SSCHA"

export NPROCS=$SLURM_NTASKS

module purge
module load Intel/OneAPI_2021.2.0

cd $SLURM_SUBMIT_DIR
cp -r ../../pseudo ./
SEED=`ls | grep 'pwi' | cut -d'.' -f1`
srun --mpi=pmi2 pw.x < $SEED.pwi > $SEED.pwo
rm -r pseudo

echo "DONE"
