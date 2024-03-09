ARG tag="22.04"
FROM ubuntu:${tag} as builder

# NOTE: although flux is in this container, we will be using flux provided by the operator
# But it makes sense to add it in case we want to disable that (and use one container)

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (might be some left over from BDF)
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y apt-transport-https ca-certificates curl clang llvm jq apt-utils wget \
         libelf-dev libpcap-dev libbfd-dev binutils-dev build-essential make \
         linux-tools-common linux-tools-$(uname -r)  \
         bpfcc-tools python3-pip git net-tools

# cmake is needed for flux-sched now!
# Note the variant is for ARM.
RUN export CMAKE=3.23.1 && \
    curl -s -L https://github.com/Kitware/CMake/releases/download/v3.23.3/cmake-3.23.3-linux-aarch64.sh > cmake.sh && \
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
# This is also the arm install
ENV  PATH=/opt/conda/bin:$PATH
RUN curl -L https://github.com/conda-forge/miniforge/releases/download/23.11.0-0/Mambaforge-23.11.0-0-Linux-aarch64.sh > mambaforge.sh && \
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
RUN git clone https://github.com/flux-framework/flux-sched /opt/flux-sched && \
    cd /opt/flux-sched && \
    git fetch && \
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

# This is needed if you intend to use EFA (HPC instance type)
# Install EFA alone without AWS OPEN_MPI
ENV EFA_VERSION=1.30.0
RUN mkdir /tmp/efa && \
    cd /tmp/efa && \
    curl -O https://s3-us-west-2.amazonaws.com/aws-efa-installer/aws-efa-installer-${EFA_VERSION}.tar.gz && \
    tar -xf aws-efa-installer-${EFA_VERSION}.tar.gz && \
    cd aws-efa-installer && \
    ./efa_installer.sh -y -g -d --skip-kmod --skip-limit-conf --no-verify
# note that with the --no-verify flag you don't get the testing libs.
# If the container does not build, you can remove it.
#    ./efa_installer.sh -y -g -d --skip-kmod --skip-limit-conf

# EFA installation complete.
# - Please logout/login to complete the installation.
# - Libfabric was installed in /opt/amazon/efa
# - Open MPI was installed in /opt/amazon/openmpi

# fi_info -p efa -t FI_EP_RDM
# Disable ptrace
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa-start.html
RUN sysctl -w kernel.yama.ptrace_scope=0

# Note we install to /usr so can be found by all users
RUN git clone --depth 1 https://github.com/lammps/lammps.git /opt/lammps
RUN  cd /opt/lammps && mkdir build && cd build &&. /etc/profile && \
    cmake ../cmake -DCMAKE_INSTALL_PREFIX:PATH=/usr -DPKG_REAXFF=yes -DBUILD_MPI=yes -DPKG_OPT=yes -DFFT=FFTW3 -DCMAKE_PREFIX_PATH=/opt/amazon/efa -DCMAKE_PREFIX_PATH=/opt/amazon/openmpi && \
    make && make install && \
    cp ./lmp /usr/bin/ && \
    cp -R /opt/lammps/examples/reaxff/HNS /home/ubuntu/lammps
