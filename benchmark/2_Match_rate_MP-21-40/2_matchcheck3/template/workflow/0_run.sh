#!/bin/bash
#SBATCH --nodes=1                     # Request 1 node
#SBATCH --ntasks-per-node=1           # Number of tasks per node (1)
#SBATCH --job-name=Nb3I8L1_vasp       # Job name (avoid using paths)
#SBATCH --output=job.out              # Standard output file
#SBATCH --error=job.err               # Standard error file
#SBATCH --time=48000:00:00            # Maximum wall time (format: [days-]hours:minutes:seconds)

echo "Begin time: $(date)"

# Configure Conda environment path and activate environment
export PATH=/opt/conda/env/chgnet/bin:$PATH
source activate chgnet

# Run Python script
python 0_run.py

echo "End time: $(date)"
