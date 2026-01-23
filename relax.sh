PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_relax"; do
    if test ! -d $DIR; then
        mkdir $DIR
    fi
done

rm -r results_relax/*
cd $PREFIX/results_relax

cat >$NAME.relax.pwi <<EOF
&CONTROL
  calculation='relax'
  restart_mode='from_scratch',
  prefix='$NAME',
  pseudo_dir = '$PSEUDO_DIR',
  outdir='$TMP_DIR',
  tstress = .true.
  tprnfor = .true.
  verbosity='high'
  forc_conv_thr = 1d-5
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
!  vdw_corr='DFT-D' !van der waals correction (works with phonons)
 /
&ELECTRONS
  conv_thr =  1d-10
  mixing_beta = 0.7
 /
&IONS
 ion_dynamics='bfgs',
 /
&CELL
 cell_dynamics='bfgs',
 press=0.0,
 press_conv_thr=0.01,
 !cell_dofree='2Dxy'
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

echo "running the relax calculation"
mpiexec -np 2 $QE_PATH/pw.x -npool $NPOOLS <$NAME.relax.pwi >$NAME.relax.pwo
rm input_tmp.in
echo "done"
