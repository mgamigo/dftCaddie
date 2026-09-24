PREFIX=$(pwd)
TMP_DIR=$PREFIX/tmp

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
  filproj='proj.dat'
  lsym=.false.
/
EOF

echo "running the projection calculation"
$QE_PATH/projwfc.x -npool $NPOOLS -in $NAME.proj.pwi >$NAME.proj.pwo
echo "done"
