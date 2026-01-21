#!/bin/bash

PREFIX=`pwd`
for DIR in "$PREFIX/GAP" ; do
    if test ! -d $DIR ; then
        mkdir $DIR
    fi
done

echo "Training the Machine Learning Potential..."

gap_fit energy_parameter_name=energy \
    force_parameter_name=forces \
    stress_parameter_name=stress \
    virial_parameter_name=dummy3 \
    do_copy_at_file=F \
    sparse_separate_file=T \
    gp_file=GAP/GAP.xml \
    at_file=sets/train.xyz \
    default_sigma={0.0009 0.03 0.03 0} \
    sparse_jitter=1.0e-8 \
    gap={soap \
        cutoff=6.42 \
        n_sparse=5000 \
        covariance_type=dot_product \
        sparse_method=cur_points \
        delta=0.205 \
        zeta=4 \
        l_max=5 \
        n_max=10 \
        atom_sigma=0.5 \
        cutoff_transition_width=0.8 \
        add_species} > GAP/fit_GAP.out

echo "DONE"
