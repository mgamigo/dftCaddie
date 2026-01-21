#!/bin/bash

$TEMPLATES/SBATCH_headings/load_sbatch_preamble.sh > master.sh
cat $TEMPLATES/qe/master_energy_surf.sh >> master.sh
chmod +x master.sh
