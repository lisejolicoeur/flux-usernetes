#!/bin/bash

set -eu pipefail

# Install a "bare metal" lammps
cd /opt
export DEBIAN_FRONTEND=noninteractive

# Note we install to /usr so can be found by all users
git clone --depth 1 --branch stable_29Sep2021_update2 https://github.com/lammps/lammps.git /opt/lammps
cd /opt/lammps
mkdir build
cd build
. /etc/profile
cmake ../cmake -D PKG_REAXFF=yes -D BUILD_MPI=yes -D PKG_OPT=yes
make
sudo make install

# install to /usr/bin
sudo mv ./lmp /usr/bin/

# examples are in:
# /opt/lammps/examples/reaxff/HNS
cp -R /opt/lammps/examples/reaxff/HNS /home/ubuntu/lammps

# clean up
rm -rf /opt/lammps

# permissions
chown -R ubuntu /home/ubuntu/lammps