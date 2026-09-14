#!/bin/bash
# === DFTCADDIE SBATCH HEADER END ===

node=$(hostname)
echo "******************"
echo "job run at node " $node
echo "NPROCS = " $NPROCS
echo "******************"
echo ""

#########################################################################
# Load modules that provide vasp_ncl, then save them with: module save VASP_modules
module purge
module restore VASP_modules

#Actual JOBS

#########################################################################

echo "DONE"
