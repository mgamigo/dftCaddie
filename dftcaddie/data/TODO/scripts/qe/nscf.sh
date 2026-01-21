PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_nscf" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_nscf/*
cd $PREFIX/results_nscf

cat > $NAME.nscf.pwi << EOF
&CONTROL
  calculation='nscf'
  restart_mode='from_scratch',
  prefix='$NAME',
  pseudo_dir = '$PSEUDO_DIR',
  outdir='$TMP_DIR',
  verbosity='high'
 /
&SYSTEM
  noncolin=.true.
  lspinorb=.true.
  ibrav=0,
  nat=$ATM_NUM,
  ntyp=$ATM_TYPES,
  ecutwfc=$CUTOFF,
  ecutrho=$ECUTRHO,
  occupations='smearing',
  smearing='mp',
  degauss=$SMEAR,
 /
&ELECTRONS
  conv_thr =  1d-10
  mixing_beta = 0.7
 /
ATOMIC_SPECIES
$ATOMIC_SPECIES
ATOMIC_POSITIONS {crystal}
$ATOMIC_CRYST_POSITIONS
K_POINTS {automatic}
  $NKGRID  0 0 0
CELL_PARAMETERS {angstrom}
$LATTICE
EOF

echo "running the nscf calculation"
srun $QE_PATH/pw.x -npool $NPOOLS < $NAME.nscf.pwi > $NAME.nscf.pwo
#srun --mpi=pmi2 $QE_PATH/pw.x -npool $NPOOLS < $NAME.nscf.pwi > $NAME.nscf.pwo
#mpiexec -np $NPROCS $QE_PATH/pw.x -npool $NPOOLS < $NAME.nscf.pwi > $NAME.nscf.pwo
rm input_tmp.in
echo "done"

