#!/bin/bash

#SBATCH --ntasks=40
#SBATCH --mem=88gb
#SBATCH -N 1
#SBATCH --time=48:00:00
#SBATCH --job-name="SSCHA"

node=`hostname`
echo "******************"
echo "job run at node " $node
echo "******************"
echo ""
#copies the directory from where you submited the job to lscratch
cp -r ../../../GAP ./
cp -r $SLURM_SUBMIT_DIR  /lscratch/$USER/$SLURM_JOB_ID 
cd /lscratch/$USER/$SLURM_JOB_ID
export NPROCS=$SLURM_NTASKS
rm slurm*.out

##########################################################################

module purge
module load ASE/3.22.1-foss-2022a
source /home/martin/Enviroments/sscha/bin/activate
PATH=$PATH:/home/martin/Cluster_scripts/templates/scripts/sscha
export PATH

echo 'Automatic Relax...'
python relax.sscha.py | tee sscha/min1.log
echo 'Generate last pop...'
python generate.pop.py | tee generate.out
echo 'Minimize last pop...'
python minimize.pop.py | tee sscha/min2.log
echo 'Compute hessian v3...'
sed -i 's/include_v4.*/include_v4 = False/g' sscha.input
python hessian.py | tee hessianv3.out
echo 'Compute hessian v4...'
sed -i 's/include_v4.*/include_v4 = True/g' sscha.input
python hessian.py | tee hessianv4.out
echo 'Compute 3rd order FC...'
sed -i 's/include_v4.*/include_v4 = False/g' sscha.input
python FC3.sscha.py | tee FC3.out

echo 'Compute the static spectral function...'
sed -i 's/no_mode_mixing.*/no_mode_mixing = False/g' sscha.input
sed -i 's/static_limit.*/static_limit = True/g' sscha.input
python spectral.sscha.py | tee static.out

echo 'Compute the dynamic spectral function...'
sed -i 's/no_mode_mixing.*/no_mode_mixing = False/g' sscha.input
sed -i 's/static_limit.*/static_limit = False/g' sscha.input
python spectral.sscha.py | tee dynamic.out

echo 'Compute no-mode-mixing spectral function...'
sed -i 's/no_mode_mixing.*/no_mode_mixing = True/g' sscha.input
python spectral.sscha.py | tee no_mixing.out

deactivate
module purge
rm -r GAP

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
rm -r BACKUP/GAP
rmdir BACKUP

echo "DONE"
