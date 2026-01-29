PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_scf"; do
    if test ! -d $DIR; then
        mkdir $DIR
    fi
done

rm -r results_scf/*
cd $PREFIX/results_scf

cat >$NAME.scf.pwi <<EOF
&CONTROL
  calculation='scf'
  restart_mode='from_scratch',
  prefix='$NAME',
  pseudo_dir = '$PSEUDO_DIR',
  outdir='$TMP_DIR',
  verbosity='high'
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
$QE_PATH/pw.x -npool $NPOOLS <$NAME.scf.pwi >$NAME.scf.pwo
cp ../tmp/$NAME.save/data-file-schema.xml ./scf.xml
rm input_tmp.in
echo "done"
