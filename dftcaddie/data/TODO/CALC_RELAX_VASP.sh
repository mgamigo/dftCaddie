#!/bin/bash

TEMPLATES=$CLUST_SCRIPTS_PATH/templates/scripts

if [ $HOSTNAME = 'ekhi.cfm.ehu.es' ]; then
	cp -v $TEMPLATES/vasp/master_ekhi.sh ./master.sh
elif [ $HOSTNAME = 'login' ]; then
	cp -v $TEMPLATES/vasp/master_planck.sh ./master.sh
elif [ $HOSTNAME = 'login4.triton.aalto.fi' ]; then
	cp -v $TEMPLATES/qe/master_triton.sh ./master.sh
fi

cp -v $TEMPLATES/vasp/INCAR_RELAX ./
cp -v $TEMPLATES/vasp/KPOINTS_SCC ./
