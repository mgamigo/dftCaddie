#!/bin/bash

cd $SLURM_SUBMIT_DIR
echo "Making backup..."
mkdir BACKUP

for file in *; do
    if [ $file != BACKUP ] && [ $file != slurm*out ]; then
        mv $file BACKUP/$file
    fi
done

echo "Copying files from /lscratch..."
cp -r $LOCAL_SCRATCH/$USER/$SLURM_JOB_ID/* $SLURM_SUBMIT_DIR/

echo "Deleting files from /lscratch..."
rm -r $LOCAL_SCRATCH/$USER/$SLURM_JOB_ID

echo "Deleting the BACKUP..."
cd $SLURM_SUBMIT_DIR
for file in *; do
    if [ $file != BACKUP ] && [ $file != slurm*out ] && [ -e BACKUP/$file ]; then
        rm -r BACKUP/$file
    fi
done
rmdir BACKUP
