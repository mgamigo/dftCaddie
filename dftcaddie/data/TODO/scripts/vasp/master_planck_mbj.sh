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
#module load VASP/5.4.4-intel-2021a-wannier90

#SCF
cp ./KPOINTS_SCC ./KPOINTS 
cp ./INCAR_SCC ./INCAR
echo "running scf calculation..."
srun --mpi=pmi2 vasp_ncl >& SCC.log
cp ./OUTCAR ./OUTCAR_SCC
cp ./DOSCAR ./DOSCAR_SCC
cp ./CHG ./CHG_SCC

#Prepare Kpoints
bash /home/$USER/Cluster_scripts/templates/scripts/vasp/Kpath_MBJ.sh

#MBJ scf and bands
cp ./INCAR_MBJ ./INCAR
cp ./KPOINTS_MBJ_BS ./KPOINTS
echo "running bands calculation..."
srun --mpi=pmi2 vasp_ncl >& MBJ.log
cp ./OUTCAR ./OUTCAR_MBJ
cp ./EIGENVAL ./EIGENVAL_MBJ
cp ./PROCAR ./PROCAR_MBJ
cp vasprun.xml vasprun_MBJ.xml

#########################################################################

echo "DONE"
