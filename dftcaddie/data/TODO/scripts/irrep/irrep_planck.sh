#!/bin/bash

output_dir=results_irreps

rm -rf $output_dir
module purge
module load Python
source /home/gutierre/Enviroments/irrep/bin/activate

mkdir $output_dir
cd tmp
PREFIX="P2Sn2"
KPOINTS="1,2,3,4,5,6"
KPNAMES="A,GM,H,K,L,M"
subsets="0_0
	0_114
	109_114
	"

for subset in $subsets; do
	echo "doing subset " $subset "..."
	low=`echo $subset | cut -f1 -d_`
	high=`echo $subset | cut -f2 -d_`
	#MAIN COMAND
	irrep -code=espresso -shiftUC=0.3333333333333,-0.3333333333333,0\
 	-prefix=$PREFIX -kpoints=$KPOINTS -kpnames=$KPNAMES -Ecut=50 -IBstart=$low -IBend=$high > output.dat
	#CLEAN

	mkdir ../$output_dir/$subset
	mv bands* ../$output_dir/$subset
	mv irrep* ../$output_dir/$subset
	mv output.dat ../$output_dir/$subset
	mv trace.txt ../$output_dir/$subset
done


deactivate
module purge
