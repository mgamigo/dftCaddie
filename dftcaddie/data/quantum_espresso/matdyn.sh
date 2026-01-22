PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp

for DIR in "$TMP_DIR" "$PREFIX/results_matdyn"; do
    if test ! -d $DIR; then
        mkdir $DIR
    fi
done

rm -r results_matdyn/*
cd $PREFIX/results_matdyn

cat >q2r.in <<EOF
&INPUT
  fildyn='../results_ph/$NAME.dyn',
  zasr='no',
  flfrc='$NAME.fc'
 /
EOF

echo "running q2r"
mpiexec -np $NPROCS q2r.x <q2r.in >q2r.out
rm input_tmp.in
echo "done"

cat >matdyn.in <<EOF
&INPUT
  flfrc='$NAME.fc',
  asr='no',
  flfrq='$NAME.freq',
  q_in_band_form=.true.,
  q_in_cryst_coord=.true.,
 /
 $QE_CRYST_PATH
EOF

echo "running matdyn"
$QE_PATH/matdyn.x <matdyn.in >matdyn.out
rm input_tmp.in
echo "done"
