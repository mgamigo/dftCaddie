PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_bands" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_bands/*
cd $PREFIX/results_bands

cat > $NAME.bands.pwi << EOF
&CONTROL
  calculation='bands'
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
K_POINTS { crystal }
 $QE_CRYST_PATH
CELL_PARAMETERS {angstrom}
$LATTICE
EOF

echo "running the bands calculation"
srun $QE_PATH/pw.x -npool $NPOOLS < $NAME.bands.pwi > $NAME.bands.pwo
#srun --mpi=pmi2 $QE_PATH/pw.x -npool $NPOOLS < $NAME.bands.pwi > $NAME.bands.pwo
#mpiexec -np $NPROCS $QE_PATH/pw.x -npool $NPOOLS < $NAME.bands.pwi > $NAME.bands.pwo
rm input_tmp.in
echo "done"

