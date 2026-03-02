PREFIX=$(pwd)
TMP_DIR=$PREFIX/RESULTS

if test ! -d $TMP_DIR; then
    mkdir $TMP_DIR
fi

cd $TMP_DIR

cp ../KPOINTS.BANDS ./KPOINTS
cp ../INCAR.BANDS ./INCAR

echo "running the scf calculation"
vasp_ncl >& BANDS.log
echo "done"
