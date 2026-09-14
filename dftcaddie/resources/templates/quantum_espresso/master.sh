#!/bin/bash
# === DFTCADDIE SBATCH HEADER END ===

node=$(hostname)
echo "******************"
echo "job run at node " $node
echo "NPROCS = " $NPROCS
echo "NPOOLS = " $NPOOLS
echo "******************"
echo ""

##########################################################################
# Load your required modules once, then save them with: module save QE_modules
module purge
module restore QE_modules

# Replace these fallback paths in your template, or set the variables in your
# environment. QE_PATH contains pw.x; PSLIBRARY is the PSLibrary root directory.
export QE_PATH="${QE_PATH:-/path/to/quantum-espresso/bin}"
export PSLIBRARY="${PSLIBRARY:-/path/to/pslibrary}"

#Load system
source SYSTEM.INFO

#Actual JOBS

#########################################################################

echo "DONE"
