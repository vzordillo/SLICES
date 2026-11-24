# Based on the nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu20.04 image
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# Switch apt repositories to the Tsinghua University mirror
RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# Update package index and install required system packages
RUN apt-get update && apt-get install -y \
    wget \
    libstdc++-9-dev \
    git \
    vim \
    g++ \
    make \
    munge \
    slurm-wlm \
    slurm-wlm-doc \
    slurm-wlm-torque 

# Download and install Miniconda
RUN wget -P /tmp https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-py39_4.10.3-Linux-x86_64.sh && \
    bash /tmp/Miniconda3-py39_4.10.3-Linux-x86_64.sh -b -p /opt/miniconda && \
    rm /tmp/Miniconda3-py39_4.10.3-Linux-x86_64.sh

# Configure environment variables
ENV PATH=/opt/miniconda/bin:$PATH

# Create the conda environment and install packages
RUN conda create -n umat python=3.10 -y

RUN /bin/bash -c "source activate umat && \
    conda install pymatgen -c conda-forge -y && \
    pip install --no-cache torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache dgl==2.1.0 -f https://data.dgl.ai/wheels/torch-2.1/cu121/repo.html && \
    pip install --no-cache torch-sparse==0.6.18 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html && \
    pip install --no-cache torch-scatter==2.1.2 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html && \
    pip install --no-cache torch-cluster==1.6.3 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html && \
    pip install --no-cache torch-spline-conv==1.2.2 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html && \
    pip install --no-cache torch-geometric==2.1.0 tensorboard==2.12.0 && \
    pip install --no-cache protobuf==4.23.3 && \
    conda install gcc=12.2.0 -c conda-forge -y &&\
    pip install --no-cache setuptools==59.5.0 && \
    pip install --no-cache alignn "

# Install jarvis_leaderboard, reinstall dgl, and install SLICES dependencies
RUN /bin/bash -c "source activate umat  && \
    pip install --no-cache jarvis_leaderboard -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip uninstall dgl -y && \
    pip install dgl -f https://data.dgl.ai/wheels/torch-2.1/cu121/repo.html && \
    pip install --no-cache slices==2.0.2 && \
    pip install --no-cache mp_api && \
    pip install --no-cache ipython  && \
    conda clean --all -f -y "

RUN /bin/bash -c "source activate umat  &&  \
    pip install jupyter -i https://pypi.tuna.tsinghua.edu.cn/simple"

# Configure .bashrc to activate the conda environment automatically
RUN echo "source /opt/miniconda/bin/activate && conda activate umat" >> /root/.bashrc

# Set environment variables
ENV PATH=/opt/miniconda/bin:$PATH \
    LD_LIBRARY_PATH=/opt/miniconda/envs/umat/lib:$LD_LIBRARY_PATH \
    DGLBACKEND=pytorch \
    DGLDEFAULTDIR=/crystal/data/.dgl 

#COPY slurm.conf /etc/slurm/

# Configure SLURM spool and runtime directories
RUN rm -rf /var/spool/slurm-llnl && \
    mkdir /var/spool/slurm-llnl && \
    chown -R slurm:slurm /var/spool/slurm-llnl && \
    rm -rf /var/run/slurm-llnl/ && \
    mkdir /var/run/slurm-llnl/ && \
    chown -R slurm:slurm /var/run/slurm-llnl/

# Set working directory
WORKDIR /crystal

# Launch bash when starting the container
CMD ["bash"]

