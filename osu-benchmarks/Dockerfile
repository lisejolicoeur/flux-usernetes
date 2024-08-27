ARG tag="22.04"
FROM ubuntu:${tag} as builder
#https://github.com/converged-computing/flux-usernetes/blob/add-azure/aws/examples/osu-benchmarks/docker/Dockerfile
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (might be some left over from BDF)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y apt-transport-https ca-certificates curl clang llvm jq apt-utils wget \
         libelf-dev libpcap-dev libbfd-dev binutils-dev build-essential make \
         linux-tools-common linux-tools-$(uname -r)  \
         bpfcc-tools python3-pip git net-tools

# cmake is needed for flux-sched now!
RUN export CMAKE=3.23.1 && \
    curl -s -L https://github.com/Kitware/CMake/releases/download/v3.23.3/cmake-3.23.3-linux-x86_64.sh > cmake.sh && \
    sh cmake.sh --prefix=/usr/local --skip-license && \
    apt-get install -y man flex ssh vim luarocks munge lcov ccache lua5.2 \
         valgrind build-essential pkg-config autotools-dev libtool \
         libffi-dev autoconf automake make clang clang-tidy \
         gcc g++ libpam-dev apt-utils \
         libsodium-dev libzmq3-dev libczmq-dev libjansson-dev libmunge-dev \
         libncursesw5-dev liblua5.2-dev liblz4-dev libsqlite3-dev uuid-dev \
         libhwloc-dev libs3-dev libevent-dev libarchive-dev \
         libboost-graph-dev libboost-system-dev libboost-filesystem-dev \
         libboost-regex-dev libyaml-cpp-dev libedit-dev uidmap dbus-user-session \
         locales

# Let's use mamba python and do away with system annoyances
ENV  PATH=/opt/conda/bin:$PATH
RUN curl -L https://github.com/conda-forge/miniforge/releases/download/23.11.0-0/Mambaforge-23.11.0-0-Linux-x86_64.sh > mambaforge.sh && \
    bash mambaforge.sh -b -p /opt/conda && \
    pip install --upgrade --ignore-installed markupsafe coverage cffi ply six pyyaml jsonschema && \
    pip install --upgrade --ignore-installed sphinx sphinx-rtd-theme sphinxcontrib-spelling

# Prepare lua rocks things... does lua really rock? Does it?
RUN apt-get install -y faketime libfaketime pylint cppcheck aspell aspell-en && \
    locale-gen en_US.UTF-8 && \
    luarocks install luaposix

# openpmix... back... back evil spirits!
RUN mkdir -p /opt/prrte && \
    cd /opt/prrte && \
    git clone https://github.com/openpmix/openpmix.git && \
    git clone https://github.com/openpmix/prrte.git && \
    set -x && \
    cd openpmix && \
    git checkout fefaed568f33bf86f28afb6e45237f1ec5e4de93 && \
    ./autogen.pl && \
    ./configure --prefix=/usr --disable-static && make -j 4 install && \
    ldconfig && \
    set +x

# prrte you are sure looking perrrty today
RUN cd /opt/prrte/prrte && \
    git checkout 477894f4720d822b15cab56eee7665107832921c && \
    ./autogen.pl && \
    ./configure --prefix=/usr && make -j 4 install

# flux security
RUN git clone --depth 1 https://github.com/flux-framework/flux-security /opt/flux-security && \
    cd /opt/flux-security && \
    ./autogen.sh && \
    PYTHON=/opt/conda/bin/python ./configure --prefix=/usr --sysconfdir=/etc && \
    make && make install

# The containers will share the same munge key.
RUN  mkdir -p /var/run/munge && \
    dd if=/dev/urandom bs=1 count=1024 > munge.key && \
    mv munge.key /etc/munge/munge.key && \
    chown -R munge /etc/munge/munge.key /var/run/munge && \
    chmod 600 /etc/munge/munge.key

# Make the flux run directory
RUN mkdir -p /home/ubuntu/run/flux

# Flux core
RUN git clone https://github.com/flux-framework/flux-core /opt/flux-core && \
    cd /opt/flux-core && \
    ./autogen.sh && \
    PYTHON=/opt/conda/bin/python PYTHON_PREFIX=PYTHON_EXEC_PREFIX=/opt/conda/lib/python3.8/site-packages ./configure --prefix=/usr --sysconfdir=/etc --runstatedir=/home/flux/run --with-flux-security && \
    make clean && \
    make && make install

# Flux pmix (must be installed after flux core)
RUN  git clone https://github.com/flux-framework/flux-pmix /opt/flux-pmix && \
  cd /opt/flux-pmix && \
  ./autogen.sh && \
  ./configure --prefix=/usr && \
  make && \
  make install

# Flux sched
RUN mkdir /opt/flux-sched && \
    cd /opt/flux-sched && \
    wget https://github.com/flux-framework/flux-sched/releases/download/v0.33.0/flux-sched-0.33.0.tar.gz && \
    tar xvf flux-sched-0.33.0.tar.gz && \
    cd /opt/flux-sched/flux-sched-0.33.0 && \
    ./autogen.sh && \
    PYTHON=/opt/conda/bin/python ./configure --prefix=/usr --sysconfdir=/etc && \
    make && make install && ldconfig && \
    echo "DONE flux build"

# Flux curve.cert
# Ensure we have a shared curve certificate
RUN flux keygen /tmp/curve.cert && \
    mkdir -p /etc/flux/system && \
    cp /tmp/curve.cert /etc/flux/system/curve.cert && \
    chmod o-r /etc/flux/system/curve.cert && \
    chmod g-r /etc/flux/system/curve.cert && \
    # Permissions for imp
    chmod u+s /usr/libexec/flux/flux-imp && \
    chmod 4755 /usr/libexec/flux/flux-imp && \
    # /var/lib/flux needs to be owned by the instance owner
    mkdir -p /var/lib/flux && \
    rm -rf /opt/flux-core /opt/flux-sched /opt/prrte /opt/flux-security

RUN  apt-get install -y clang-format ffmpeg
# Disable ptrace
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa-start.html
RUN sysctl -w kernel.yama.ptrace_scope=0

RUN apt-get update && apt-get install -y git wget g++ gcc build-essential \
    openssh-client openssh-server openmpi-bin libopenmpi-dev libgtk2.0-dev \
    net-tools libc6-dev rdma-core infiniband-diags libibverbs-dev libibverbs1 librdmacm1 libucx0 ibverbs-utils

WORKDIR /opt
RUN wget --no-check-certificate http://mvapich.cse.ohio-state.edu/download/mvapich/osu-micro-benchmarks-7.4.tar.gz
RUN tar xvf osu-micro-benchmarks-7.4.tar.gz
WORKDIR osu-micro-benchmarks-7.4/
RUN ./configure CC=mpicc CFLAGS=-I$(pwd)/../src/osu-micro-benchmarks-7.4/util --prefix=$(pwd)
RUN make & make install

ENV PATH=$PATH:/opt/osu-benchmark/build.openmpi/mpi/startup:/opt/osu-benchmark/build.openmpi/mpi/collective:/opt/osu-benchmark/build.openmpi/mpi/pt2pt:/opt/osu-benchmark/build.openmpi/mpi/one-sided
