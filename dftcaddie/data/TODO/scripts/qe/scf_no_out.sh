PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_scf" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_scf/*
cd $PREFIX/results_scf

cat > $NAME.scf.pwi << EOF
&CONTROL
  calculation='scf'
  disk_io = "none"
  prefix='$NAME',
  pseudo_dir = '$PSEUDO_DIR',
  tstress = .true.
  tprnfor = .true.
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
  $KGRID  0 0 0
CELL_PARAMETERS {angstrom}
$LATTICE
EOF

echo "running the scf calculation"
srun $QE_PATH/pw.x -npool $NPOOLS < $NAME.scf.pwi > $NAME.scf.pwo
#srun --mpi=pmi2 $QE_PATH/pw.x -npool $NPOOLS < $NAME.scf.pwi > $NAME.scf.pwo
#mpiexec -np $NPROCS $QE_PATH/pw.x -npool $NPOOLS < $NAME.scf.pwi > $NAME.scf.pwo
rm input_tmp.in
echo "done"

