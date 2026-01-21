PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_fermi" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_fermi/*
cd $PREFIX/results_fermi

cat > $NAME.pp.fs.pwi << EOF
&FERMI
  prefix='$NAME',
  outdir='$TMP_DIR',
 /
EOF

echo "processing the fermi surface calculation"
srun $QE_PATH/fs.x -npool $NPOOLS < $NAME.pp.fs.pwi > $NAME.pp.fs.pwo
#srun --mpi=pmi2 $QE_PATH/fs.x -npool $NPOOLS < $NAME.pp.fs.pwi > $NAME.pp.fs.pwo
#mpiexec -np $NPROCS $QE_PATH/fs.x -npool $NPOOLS < $NAME.pp.fs.pwi > $NAME.pp.fs.pwo
rm input_tmp.in
echo "done"
