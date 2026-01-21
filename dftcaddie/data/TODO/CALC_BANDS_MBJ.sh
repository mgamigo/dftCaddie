#!/bin/bash

if [ $HOSTNAME = 'ekhi.cfm.ehu.es' ]; then
	cp -v $TEMPLATES/vasp/master_ekhi_mbj.sh ./master.sh
elif [ $HOSTNAME = 'login' ]; then
	cp -v $TEMPLATES/vasp/master_planck_mbj.sh ./master.sh
elif [ $HOSTNAME = 'login4.triton.aalto.fi' ]; then
	cp -v $TEMPLATES/qe/master_triton.sh ./master.sh
fi
cp -v $TEMPLATES/vasp/INCAR_SCC ./
cp -v $TEMPLATES/vasp/INCAR_MBJ ./
cp -v $TEMPLATES/vasp/KPOINTS_SCC ./
