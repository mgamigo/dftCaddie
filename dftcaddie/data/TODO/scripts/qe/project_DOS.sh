PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_proj" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_proj/*
cd $PREFIX/results_proj

cat > $NAME.proj.pwi << EOF
&PROJWFC
  prefix='$NAME',
  outdir='$TMP_DIR',
  lwrite_overlaps=.true.
  filpdos='pdos.dat'
/
EOF

echo "running the projection calculation"
srun $QE_PATH/projwfc.x < $NAME.proj.pwi > $NAME.proj.pwo
#srun --mpi=pmi2 $QE_PATH/projwfc.x < $NAME.proj.pwi > $NAME.proj.pwo
#mpiexec -np $NPROCS $QE_PATH/projwfc.x < $NAME.proj.pwi > $NAME.proj.pwo
rm input_tmp.in
echo "done"

