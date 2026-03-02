#!/bin/bash
# === DFTCADDIE SBATCH HEADER END ===

node=$(hostname)
echo "******************"
echo "job run at node " $node
echo "NPROCS = " $NPROCS
echo "******************"
echo ""

#########################################################################
module purge
module restore VASP_modules

#Actual JOBS

#########################################################################

echo "DONE"
