#!/bin/bash
# === DFTCADDIE SBATCH HEADER END ===

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
