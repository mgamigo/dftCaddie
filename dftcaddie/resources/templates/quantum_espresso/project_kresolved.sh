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
  ngauss=0,
  degauss=0.001,
  filpdos='pdos.dat'
  kresolveddos=.true.
  filproj='proj.dat'
/
EOF

echo "running the projection calculation"
$QE_PATH/projwfc.x -npool $NPOOLS -in $NAME.proj.pwi >$NAME.proj.pwo
echo "done"
