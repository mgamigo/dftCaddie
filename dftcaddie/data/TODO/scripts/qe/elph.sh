PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp

for DIR in "$TMP_DIR" "$PREFIX/results_elph" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done 
rm -r results_elph/*
cd $PREFIX/results_elph

cat > $NAME.elph.pwi << EOF
&INPUTPH
  prefix='$NAME',
  outdir='$TMP_DIR/',
  fildyn='../results_ph/$NAME.dyn',
  fildvscf='dv'
  tr2_ph=1e-20
  alpha_mix=0.5,
  verbosity='high'
  electron_phonon = 'simple',
  trans = .false.,
  el_ph_sigma = 0.001
  el_ph_nsigma = 10
  nk1 = 32
  nk2 = 32
  nk3 = 20
  k1 = 1
  k2 = 1
  k3 = 1
 /
0.000000000  -0.577350269  -0.295154966
EOF

echo "running the electron-phonon calculation"
srun $QE_path/ph.x -npool $NPOOLS < $NAME.elph.pwi > $NAME.elph.pwo
#srun --mpi=pmi2 $QE_path/ph.x -npool $NPOOLS < $NAME.elph.pwi > $NAME.elph.pwo
#mpiexec -np $NPROCS $QE_path/ph.x -npool $NPOOLS < $NAME.elph.pwi > $NAME.elph.pwo
rm input_tmp.in
echo "done"
