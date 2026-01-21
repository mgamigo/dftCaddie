#!/bin/bash
 
#SBATCH --nodes=1
#SBATCH --ntasks=40
#SBATCH --mem=88gb
#SBATCH --time=48:00:00
#SBATCH --job-name="NONAME"

 node=`hostname`
echo "******************"
echo "job run at node " $node
echo "******************"
echo ""

#IF PARALELIZING PHONONS
#cp -r ../../../tmp ./

#copies the directory from where you submited the job to lscratch
cp -r $SLURM_SUBMIT_DIR  /lscratch/$USER/$SLURM_JOB_ID 
cd /lscratch/$USER/$SLURM_JOB_ID
export NPROCS=$SLURM_NTASKS
rm slurm*.out

##########################################################################
module purge
module load VASP/6.4.2-intel-2021a-wannier90

#SCF
cp ./KPOINTS_SCC ./KPOINTS 
cp ./INCAR_SCC ./INCAR
echo "running scf calculation..."
mpirun -np $NPROCS vasp_ncl >& SCC.log
cp ./OUTCAR ./OUTCAR_SCC
cp ./DOSCAR ./DOSCAR_SCC
cp ./CHG ./CHG_SCC

#Bands
cp ./INCAR_BS ./INCAR
cp ./KPOINTS_BS ./KPOINTS
echo "running bands calculation..."
mpirun -np $NPROCS vasp_ncl >& BS.log
cp ./OUTCAR ./OUTCAR_BS
cp ./EIGENVAL ./EIGENVAL_BS
cp ./PROCAR ./PROCAR_BS
cp vasprun.xml vasprun_BS.xml

#########################################################################

cd $SLURM_SUBMIT_DIR
echo "Copying files from /lscratch..."

cp -r /lscratch/$USER/$SLURM_JOB_ID $SLURM_SUBMIT_DIR/RESULTS

echo "Deleting files from /lscratch..."
rm -r /lscratch/$USER/$SLURM_JOB_ID

echo "DONE"
