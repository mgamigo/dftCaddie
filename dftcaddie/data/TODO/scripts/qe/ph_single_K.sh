PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp

for DIR in "$TMP_DIR" "$PREFIX/results_ph" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done 
rm -r results_ph/*
cd $PREFIX/results_ph

cat > $NAME.ph.pwi << EOF

&INPUTPH
  prefix='$NAME',
  recover=.true.
  outdir='$TMP_DIR/',
  fildyn='$NAME.dyn',
  fildvscf='dv',
  tr2_ph=1e-17
  alpha_mix=0.5,
  verbosity='high'
 /
 0.0  0.0   0.0
EOF

echo "running the phonons calculation"
srun $QE_PATH/ph.x -npool $NPOOLS < $NAME.ph.pwi > $NAME.ph.pwo
#srun --mpi=pmi2 $QE_PATH/ph.x -npool $NPOOLS < $NAME.ph.pwi > $NAME.ph.pwo
#mpiexec -np $NPROCS $QE_PATH/ph.x -npool $NPOOLS < $NAME.ph.pwi > $NAME.ph.pwo
rm input_tmp.in
echo "done"
