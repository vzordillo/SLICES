# Docker Configuration

Docker setup files for containerized SLICES execution.

## Files

- `Dockerfile` - Docker image definition
- `docker-compose.yml` - Docker Compose configuration
- `entrypoint_set_cpus.sh` - Entrypoint script for CPU configuration
- `entrypoint_set_cpus_jupyter.sh` - Entrypoint script for Jupyter with CPU configuration
- `slurm.conf` - SLURM job scheduler configuration

## Usage

```bash
# Build Docker image
docker build -f docker/Dockerfile -t slices .

# Run with Docker Compose
docker-compose -f docker/docker-compose.yml up
```

