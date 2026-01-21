#!/bin/bash

#SBATCH --ntasks=20
#SBATCH --mem=750gb
#SBATCH -N 1
#SBATCH --time=240:00:00
#SBATCH --job-name="GAP"
#SBATCH --partition=fat

node=`hostname`
echo "******************"
echo "job run at node " $node
echo "******************"
echo ""

#copies the directory from where you submited the job to lscratch
cp -r $SLURM_SUBMIT_DIR  /lscratch/$USER/$SLURM_JOB_ID 
cd /lscratch/$USER/$SLURM_JOB_ID
export NPROCS=$SLURM_NTASKS
NPOOLS=`python -c "print($NPROCS / 4)"`
export NPOOLS
rm slurm*.out

##########################################################################

module purge
module load ASE/3.22.1-foss-2022a
source /home/martin/Enviroments/sscha/bin/activate

bash fit_GAP.sh

#python test_GAP.py | tee test_GAP.out
#mv test_GAP.out test_GAP/test_GAP.out

#python get_phonons.py | tee phonon_GAP.out

deactivate
module purge
#########################################################################

cd $SLURM_SUBMIT_DIR
echo "Making backup..."
mkdir BACKUP

for file in *; do
	if [ $file != BACKUP ] && [ $file != slurm*out ]; then
		mv $file BACKUP/$file
	fi
done

echo "Copying files from /lscratch..."
cp -r /lscratch/$USER/$SLURM_JOB_ID/* $SLURM_SUBMIT_DIR/

echo "Deleting files from /lscratch..."
rm -r /lscratch/$USER/$SLURM_JOB_ID

echo "Deleting the BACKUP..."
cd $SLURM_SUBMIT_DIR
for file in *; do
	if [ $file != BACKUP ] && [ $file != slurm*out ] && [ -e BACKUP/$file ]; then
		rm -r BACKUP/$file
	fi
done
rmdir BACKUP

echo "DONE"
