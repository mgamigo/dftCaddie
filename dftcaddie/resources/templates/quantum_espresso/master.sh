#!/bin/bash
# === DFTCADDIE SBATCH HEADER END ===

##########################################################################
# Load your required modules once, then save them with: module save QE_modules
module purge
module restore QE_modules

#Load system
source SYSTEM.INFO
# Replace this fallback path or set QE_PATH in your environment.
# PSEUDO_DIR is set and exported by SYSTEM.INFO.
export QE_PATH="${QE_PATH:-/path/to/quantum-espresso/bin}"

#Actual JOBS

#########################################################################

echo "DONE"
