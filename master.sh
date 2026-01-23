#!/bin/bash

node=$(hostname)
echo "******************"
echo "job run at node " $node
echo "******************"
echo ""

export QE_PATH=$SOFTWARE/qe-7.3/bin
export PSLIBRARY=$SOFTWARE/PSEUDOS/pslibrary

##########################################################################
module purge
module restore QE_modules

#Load system
source SYSTEM.INFO

#Actual JOBS

#########################################################################

echo "DONE"
