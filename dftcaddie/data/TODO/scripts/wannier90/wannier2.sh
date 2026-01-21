PREFIX=`pwd`
TMP_DIR=$PREFIX/tmp
FERMI=`grep Fermi results_nscf/*nscf.pwo | awk '{print $5}'`

for DIR in "$TMP_DIR" "$PREFIX/results_wannier90" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

cd $PREFIX/results_wannier90

cat > $NAME.pw2wan.in << EOF
&inputpp
  outdir='$TMP_DIR',
  prefix='$NAME',
  seedname = '$NAME'
  spin_component = 'none'
/
EOF

echo "running the pw2wan calculation to generate .mmn () and .amn files"
echo ".mmn : Block states overlap"
echo ".amn : Projections for the starting guess"
mpiexec -np $NPROCS pw2wannier90.x < $NAME.pw2wan.in > $NAME.pw2wan.out
#Planck
#srun --mpi=pmi2 pw2wannier90.x < $NAME.pw2wan.in > $NAME.pw2wan.out
echo "done"

