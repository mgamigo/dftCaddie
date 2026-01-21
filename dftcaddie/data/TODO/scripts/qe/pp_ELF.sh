PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
PSEUDO_DIR=$PSLIBRARY/$EXCHANGE/PSEUDOPOTENTIALS

for DIR in "$TMP_DIR" "$PREFIX/results_pp_ELF" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

rm -r results_pp_ELF/*
cd $PREFIX/results_pp_ELF

cat > $NAME.pp.ELF.in << EOF
&INPUTPP
  prefix='$NAME',
  outdir='$TMP_DIR',
  filplot='ELF.tmp.dat'
  plot_num=8
 /
&PLOT
  fileout='$NAME.ELF.xsf'
  iflag=3
  output_format=5
  e1(1)=1.0, e1(2)=0.0, e1(3)=0.0,
  e2(1)=0.0, e2(2)=1.0, e2(3)=0.0,
  e3(1)=0.0, e3(2)=0.0, e3(3)=1.0,
  x0(1)=0.0, x0(2)=0.0, x0(3)=0.0,
 /
EOF

echo "processing the ELF calculation"
srun $QE_PATH/pp.x -npool $NPOOLS < $NAME.pp.ELF.in > $NAME.pp.ELF.out
#srun --mpi=pmi2 $QE_PATH/pp.x -npool $NPOOLS < $NAME.pp.ELF.in > $NAME.pp.ELF.out
#mpirun -np $NPROCS $QE_PATH/pp.x -npool $NPOOLS < $NAME.pp.ELF.in > $NAME.pp.ELF.out
rm ELF.tmp.dat
rm input_tmp.in
echo "done"
