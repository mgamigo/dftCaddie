PREFIX=$(pwd)
TMP_DIR=$PREFIX/RESULTS

if test ! -d $TMP_DIR; then
    mkdir $TMP_DIR
fi

cd $TMP_DIR

cp ../KPOINTS.SCC ./KPOINTS
cp ../INCAR.RELAX ./INCAR

echo "running the scf calculation"
vasp_ncl >& RELAX.log
echo "done"
