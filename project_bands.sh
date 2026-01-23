PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_proj"; do
    if test ! -d $DIR; then
        mkdir $DIR
    fi
done

rm -r results_proj/*
cd $PREFIX/results_proj

cat >$NAME.proj.pwi <<EOF
&PROJWFC
  prefix='$NAME',
  outdir='$TMP_DIR',
  ngauss=0, degauss=0.001
  kresolveddos=.true.
  filpdos='pdos.dat'
  filproj='proj.dat'
/
EOF

echo "running the projection calculation"
mpiexec -np 2 $QE_PATH/projwfc.x <$NAME.proj.pwi >$NAME.proj.pwo
rm input_tmp.in
echo "done"
