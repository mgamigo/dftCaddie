#!/bin/bash

TEMPLATES=$CLUST_SCRIPTS_PATH/templates/scripts

if [ $HOSTNAME = 'ekhi.cfm.ehu.es' ]; then
	cp -v $TEMPLATES/qe/master_ekhi.sh ./master.sh
	cp -v $TEMPLATES/irrep/irrep_ekhi.sh ./irrep.sh
elif [ $HOSTNAME = 'login' ]; then
	cp -v $TEMPLATES/qe/master_planck.sh ./master.sh
	cp -v $TEMPLATES/irrep/irrep_planck.sh ./irrep.sh
elif [ $HOSTNAME = 'login4.triton.aalto.fi' ]; then
	cp -v $TEMPLATES/qe/master_triton.sh ./master.sh
	cp -v $TEMPLATES/irrep/irrep_triton.sh ./irrep.sh
fi
cp -v $TEMPLATES/qe/scf.sh ./
cp -v $TEMPLATES/qe/bands_irrep.sh ./
cp -v $TEMPLATES/qe/bands_irrep.sh ./
