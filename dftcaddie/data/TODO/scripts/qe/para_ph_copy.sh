#!/bin/bash

echo Copying temporary files for phonon paralelization...
cp -r $SLURM_SUBMIT_DIR/../../../tmp ./
cp -r $SLURM_SUBMIT_DIR/../../../SYSTEM.INFO ./
