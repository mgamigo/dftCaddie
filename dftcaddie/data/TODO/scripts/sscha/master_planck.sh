#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks=96
#SBATCH --mem=180gb
#SBATCH --partition=intelnodes
#SBATCH --time=240:00:00
#SBATCH --job-name="SSCHA"

##########################################################################

module purge
module load ASE/3.19.0-foss-2018b-Python-3.6.6
source /home/gutierre/Enviroments/sscha/bin/activate
PATH=$PATH:/zfs_data/gutierre/Cluster_scripts/templates/scripts/sscha
export PATH

cp -r ../../../GAP ./

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

echo "DONE"
