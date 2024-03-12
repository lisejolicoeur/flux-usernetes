FROM ghcr.io/rse-ops/lammps-efa:ubuntu-22.04

RUN pip install riverapi && \
    pip install river
ENV PATH=/opt/conda/bin:$PATH

WORKDIR /code
COPY ./scripts /code
WORKDIR /opt/lammps/examples/reaxff/HNS
