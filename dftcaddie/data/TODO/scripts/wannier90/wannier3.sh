PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
FERMI=`grep Fermi results_nscf/*nscf.pwo | awk '{print $5}'`

for DIR in "$TMP_DIR" "$PREFIX/results_wannier90" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

cd $PREFIX/results_wannier90

echo "computing the MLWFs"
mpiexec -np $NPROCS wannier90.x $NAME.win
#Planck
#srun --mpi=pmi2 wannier90.x $NAME.win
echo done
