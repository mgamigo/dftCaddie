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
export PSLIBRARY=$SOFTWARE/PSEUDOS/pslibrary/pbe/PSEUDOPOTENTIALS

##########################################################################
module purge
module restore QE_modules

FILE=`ls | grep 'pwi'`
sed -i "s|pseudo_dir.*|pseudo_dir = '$PSLIBRARY'|g" "$FILE"
SEED=${FILE::-4}
srun $QE_PATH/pw.x -npool $NPOOLS < $SEED.pwi > $SEED.pwo
#srun --mpi=pmi2 $QE_PATH/pw.x -npool $NPOOLS < $SEED.pwi > $SEED.pwo
#mpiexec -np $NPROCS $QE_PATH/pw.x -npool $NPOOLS < $SEED.pwi > $SEED.pwo

#########################################################################

#COPY FROM $LOCAL_SCRATCH
$TEMPLATES/GENERALS/Copy_from_lscratch.sh

echo "DONE"
