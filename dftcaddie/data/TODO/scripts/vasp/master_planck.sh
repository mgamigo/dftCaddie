#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=96
#SBATCH --time=240:00:00
#SBATCH --partition=intelnodes
#SBATCH --mem=188gb
#SBATCH --job-name="NONAME"

node=`hostname`
echo "******************"
echo "job run at node " $node
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
cp ./INCAR_SCC ./INCAR
echo "scf calculation..."
srun --mpi=pmi2 vasp_ncl >& SCC.log
# Guardo los ficheros de densidad de carga y el OUTCAR
cp ./OUTCAR ./OUTCAR_SCC
cp ./CHG ./CHG_SCC
# Preparo mis ficheros para el calculo de bandas y lanzo VASP otra vez
cp ./INCAR_BS ./INCAR
cp ./KPOINTS_BS ./KPOINTS
echo "BS calculation..."
srun --mpi=pmi2 vasp_ncl >& BS.log
cp ./OUTCAR ./OUTCAR_BS
cp ./EIGENVAL ./EIGENVAL_BS
cp vasprun.xml vasprun_BS.xml

#########################################################################

echo "DONE"
