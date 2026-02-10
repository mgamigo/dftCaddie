#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=96
#SBATCH --time=240:00:00
#SBATCH --partition=intelnodes
#SBATCH --mem=188gb
#SBATCH --job-name="LSe-Se"

node=`hostname`
echo "******************"
echo "job run at node " $node
echo "NPROCS = " $NPROCS
echo "******************"
echo ""

export NPROCS=$SLURM_NTASKS
cd $SLURM_SUBMIT_DIR

#########################################################################

mkdir RESULTS
cp * RESULTS
cd RESULTS

module purge
module load VASP/vasp_6.4.2

# Calculo autoconsistente
cp ./KPOINTS_SCC ./KPOINTS
cp ./INCAR_RELAX ./INCAR
echo "scf calculation..."
srun --mpi=pmi2 vasp_ncl >& RELAX.log

#########################################################################

echo "DONE"
