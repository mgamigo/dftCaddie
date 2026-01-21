#!/bin/bash
#
# Obtain the cluster name by:
# ->    scontrol show config | grep -i clustername

if echo "$SLURM_CLUSTER_NAME" | grep -q "ekhi"; then					#Ekhi
    echo $SLURM_CLUSTER_NAME
	#module load intel/2021a
elif [[ "$SLURM_CLUSTER_NAME" == "cpfs-cluster" ]]; then						#Planck
    echo $SLURM_CLUSTER_NAME
	#module load Intel/OneAPI_2024.0.1
elif echo "$SLURM_CLUSTER_NAME" | grep -q "triton"; then				#Triton
    echo $SLURM_CLUSTER_NAME
	#module load gcc/12.3.0 openmpi/4.1.6 python
elif echo "$SLURM_CLUSTER_NAME" | grep -q "puhti"; then				#Puhti
    echo $SLURM_CLUSTER_NAME
	#module load intel-oneapi-compilers-classic/2021.6.0 intel-oneapi-mpi/2021.6.0 intel-oneapi-mkl/2022.1.0 cmake/3.23.1
elif echo "$SLURM_CLUSTER_NAME" | grep -q "mahti"; then				#Mahti
    echo $SLURM_CLUSTER_NAME
	#module load gcc/9.4.0 openmpi/4.1.2 openblas/0.3.18-omp netlib-scalapack/2.1.0 fftw/3.3.10-mpi-omp cmake/3.21.4
fi


