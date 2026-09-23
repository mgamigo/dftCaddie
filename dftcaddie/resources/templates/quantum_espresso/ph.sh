PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp

for DIR in "$TMP_DIR" "$PREFIX/results_ph"; do
    if test ! -d $DIR; then
        mkdir $DIR
    fi
done

rm -r results_ph/*
cd $PREFIX/results_ph

read -r PH_NQ1 PH_NQ2 PH_NQ3 <<<"$PHGRID"
cat >$NAME.ph.pwi <<EOF
&INPUTPH
  prefix='$NAME',
  recover=.true.
  outdir='$TMP_DIR/',
  fildyn='$NAME.dyn',
  ldisp=.true.,
  tr2_ph=1e-17
  alpha_mix=0.5,
  verbosity='high'
  nq1=$PH_NQ1, nq2=$PH_NQ2, nq3=$PH_NQ3,
 /
EOF

echo "running the phonons calculation"
$QE_PATH/ph.x -npool $NPOOLS -in $NAME.ph.pwi >$NAME.ph.pwo
rm input_tmp.in
echo "done"
