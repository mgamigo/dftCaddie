#!/bin/bash

echo "Copying files to /lscratch..."
mkdir -p $LOCAL_SCRATCH/$USER/$SLURM_JOB_ID
cp -r $SLURM_SUBMIT_DIR/* $LOCAL_SCRATCH/$USER/$SLURM_JOB_ID
cd $LOCAL_SCRATCH/$USER/$SLURM_JOB_ID
rm slurm*.out
