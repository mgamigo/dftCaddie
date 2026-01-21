#!/bin/bash
#
if echo "$HOSTNAME" | grep -q "ekhi"; then #Ekhi
    cat $TEMPLATES/SBATCH_headings/ekhi
elif [[ "$HOSTNAME" == "login" ]]; then #Planck
    cat $TEMPLATES/SBATCH_headings/planck
elif echo "$HOSTNAME" | grep -q "triton"; then #Triton
    cat $TEMPLATES/SBATCH_headings/triton
elif echo "$HOSTNAME" | grep -q "puhti"; then #Puhti
    cat $TEMPLATES/SBATCH_headings/puhti_mahti
elif echo "$HOSTNAME" | grep -q "mahti"; then #Mahti
    cat $TEMPLATES/SBATCH_headings/puhti_mahti
else
    cat $TEMPLATES/SBATCH_headings/default
fi
