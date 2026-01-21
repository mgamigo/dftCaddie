#!/bin/bash

TEMPLATES=$CLUST_SCRIPTS_PATH/templates/scripts

if [ $HOSTNAME = 'ekhi.cfm.ehu.es' ]; then
	cp -v $TEMPLATES/sscha/master_ekhi.sh ./master.sh
elif [ $HOSTNAME = 'login' ]; then
	cp -v $TEMPLATES/sscha/master_planck.sh ./master.sh
elif [ $HOSTNAME = 'login4.triton.aalto.fi' ]; then
	cp -v $TEMPLATES/qe/master_triton.sh ./master.sh
fi

cp -v $TEMPLATES/sscha/hessian.py ./
cp -v $TEMPLATES/sscha/minimize.pop.py ./
cp -v $TEMPLATES/sscha/relax.sscha.py ./
cp -v $TEMPLATES/sscha/generate.pop.py ./
cp -v $TEMPLATES/sscha/FC3.sscha.py ./
cp -v $TEMPLATES/sscha/spectral.sscha.py ./
