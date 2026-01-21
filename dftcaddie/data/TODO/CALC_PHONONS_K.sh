#!/bin/bash

$TEMPLATES/SBATCH_headings/load_sbatch_preamble.sh > master.sh
cat $TEMPLATES/qe/master.sh >> master.sh
JOBS_LINE=`grep -n "#Actual JOBS" master.sh | cut -f1 -d:`

STEPS=(
    scf.sh
    ph_single_K.sh
	matdyn.sh
)

for S in ${STEPS[@]}; do
    cp -v "$TEMPLATES/qe/$S" ./
	Insert $JOBS_LINE "bash $S" master.sh
	((JOBS_LINE+=1))
done
chmod +x master.sh
