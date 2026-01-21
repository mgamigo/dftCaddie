#!/bin/bash

if [ $HOSTNAME = 'ekhi.cfm.ehu.es' ]; then
    #module purge
    module load ASE/3.19.0-foss-2018b-Python-3.6.6
    source /home/martin/Enviroments/std/bin/activate
    python /home/$USER/Cluster_scripts/templates/scripts/vasp/Kpath_MBJ.py
    deactivate
elif [ $USER = 'gutierre' ]; then
    python /home/$USER/Cluster_scripts/templates/scripts/vasp/Kpath_MBJ.py
fi


