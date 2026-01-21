node=`hostname`
echo "******************"
echo "job run at node " $node
echo "******************"
echo ""

#COPY TO $LOCAL_SCRATCH (source is necessary)
source $TEMPLATES/GENERALS/Copy_to_lscratch.sh

export NPROCS=$SLURM_NTASKS
NPOOLS=`python3 -c "print($NPROCS / 4)"`
export NPOOLS

export QE_PATH=$SOFTWARE/qe-7.3/bin
export PSLIBRARY=$SOFTWARE/PSEUDOS/pslibrary

##########################################################################
module purge
module restore QE_modules

#IF PARALELIZING PHONONS
$TEMPLATES/qe/para_ph_copy.sh

#Load system
source SYSTEM.INFO

#Actual JOBS

#IF PARALELIZING PHONONS
$TEMPLATES/qe/para_ph_clean.sh

#########################################################################

#COPY FROM $LOCAL_SCRATCH
$TEMPLATES/GENERALS/Copy_from_lscratch.sh

echo "DONE"
