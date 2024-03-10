# OSU Benchmarks
  
Let's again compare bare metal to usernetes

1. run on bare metal with lammps + flux
2. run on bare metal with lammps in container + flux
3. run in usernetes with same container and lammps
4. run on bare metal (with and without container) but with usernetes running (to assess overhead)
 
```bash
docker build -t ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04 .
docker push  ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04
```

## Run Experiments

### 1. Bare Metal with Flux

```bash
# This is where the example is
mkdir -p /home/ubuntu/osu
cd /home/ubuntu/osu

# Create output directory for results
mkdir -p ./results/bare-metal
```

#### Testing commands

These are installed to the host, at the same version as in the container.

```bash
binary=/usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allgather
flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task $binary
```

For the set, I'm going to stick with what we [decided before](https://github.com/converged-computing/metrics-operator-experiments/blob/main/google/kubecon/osu-benchmarks/run6/crd/metrics-64.yaml):

- all_reduce
- osu_hello
- osu_latency


```bash
screen /bin/bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    # Run for each of the above tasks - this should be ALL nodes
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allgather  |& tee ./results/bare-metal/all_gather-${i}.out
    # And these just two
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/startup/osu_hello  |& tee ./results/bare-metal/osu_hello-${i}.out
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency  |& tee ./results/bare-metal/osu_latency-${i}.out
done
```

I chose 45 seconds anticipating that the usernetes will be about twice as slow. We are still running on two nodes, so will need
to adjust accordingly after doing an initial test (e.g., extrapolate difference in 2 vs N nodes based on differences between usernetes / bare metal for 2).

### 2. Container LAMMPS with Flux

Note that the container is built from [docker](docker).

```bash
cd /home/ubuntu/lammps
flux exec --rank all --dir /home/ubuntu/lammps singularity pull docker://ghcr.io/rse-ops/lammps-efa:ubuntu-22.04
container=/home/ubuntu/lammps/lammps-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container

# Here is a test run - this took again 45 seconds
flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 8 -v y 8 -v z 8 -in ./in.reaxff.hns

# Run the same loop, but in the container
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 8 -v y 8 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container/lammps-${i}.out
done
```

### 3. Flux Operator with Lammps

We have efa working in the flux operator, but it is still really slow regardless, but I haven't been able to test on >1 node.

This comes down to installing the operator and submitting the same job with usernetes. You should already have usernetes setup per instructions in the top level aws README. Note that we are going to be using version 2 (refactor) of the Flux Operator. After you have the control plane and all kubelets running, let's install it.

```bash
# Autocomplete
source <(kubectl completion bash) 

# Sanity check your cluster is there...
kubectl get nodes
```
```console
NAME                      STATUS   ROLES           AGE   VERSION
u7s-i-007675dd8fe752491   Ready    control-plane   45m   v1.29.1
u7s-i-062265c6a447abe58   Ready    <none>          42m   v1.29.1
```

We are going to install the efa plugin (terribly tweaked by me to get it working...) and the Flux Operator, pinned to a specific release for ARM. It's easiest to clone this repository to interact, likely.

```bash
git clone https://github.com/converged-computing/flux-usernetes /home/ubuntu/lammps/flux-usernetes

# This is run from /home/ubuntu/lammps
kubectl apply -f ./flux-usernetes/aws/examples/lammps/crd/efa-device-plugin.yaml 
kubectl apply -f ./flux-usernetes/aws/examples/lammps/crd/flux-operator-arm.yaml

# Make sure it's running
kubectl logs -n operator-system operator-controller-manager-547869d677-8pqmt 
```

Let's get the lammps configuration - it's in this repository [crd/minicluster-efa.yaml](crd/minicluster-efa.yaml)
I recommended copying into your present working directory and tweaking for the cluster size that you have. E.g.,

```console
cp flux-usernetes/aws/examples/lammps/crd/minicluster-efa.yaml .
vim ...
```

Remember that you'll typically need to ask for one fewer note than you have because we don't schedule to the control plane.
E.g., 3 nodes on AWS == run the minicluster at size 2. First do a setup and test run:

```bash
# Create output directory for results
mkdir -p ./results/usernetes

# Run once to pull containers to nodes (this will be thrown away)
kubectl apply -f ./minicluster-efa.yaml

# Test these commands before running in loop
pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)

# This will stream until it finishes
echo "Lead broker pod is ${pod}"
kubectl logs ${pod} -f |& tee /tmp/test.out

# And this absolutely waits until the job is deemed complete
kubectl wait --for=condition=complete job/flux-sample
kubectl delete -f ./minicluster-efa.yaml --wait=true
```

#### Timing Testing

From basic testing, on two nodes (comparing in Usernetes with EFA and on bare metal with EFA) lammps took:

- Problem size 8x8x8 (efa) on 2 nodes
 - 45 seconds on bare metal
 - 112 seconds in Usernetes

- Problem size 16x8x8 (efa) on 2 nodes
 - 83 seconds on bare metal
 - 196 seconds in Usernetes

- Problem size 16x16x8 (efa) on 2 nodes
 - 157 seconds on bare metal
 - 300 seconds in Usernetes (5 minutes)

- Problem size 32x16x8 (efa) on 2 nodes (this is too long I think)
 - 83 seconds on bare metal
 - 727 seconds in Usernetes (12 minutes, 7 seconds)

I'm going to need to test the other end - likely 17 nodes for size 16, to decide on the range. For example, if usernetes scales really badly and the times are bad, we can't choose a problem size that is too big for that.

```bash
for i in $(seq 1 20); do 
    echo "Running iteration ${i}"
    kubectl apply -f ./minicluster-efa.yaml 
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    # Wait for init to finish and pod to initialize
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    # This waits for lammps to finish (streaming the log)
    kubectl logs ${pod} -f |& tee ./results/usernetes/lammps-${i}.out
    # And an extra precaution the entire job/workers are complete
    kubectl wait --for=condition=complete --timeout=120s job/flux-sample
    kubectl delete -f ./minicluster-efa.yaml --wait=true
done
```

Ensure you clean up (delete the flux operator) when you are done.

```bash
kubectl delete -f ./crd/flux-operator-arm.yaml
```

## Debugging

Installing the efa testing tool (binary) in the flux operator running container. Note you'll want to change the command to sleep infinity so you have resources!

```
cd /tmp
git clone https://github.com/ofiwg/libfabric
cd ./libfabric
./autogen.sh
mkdir -p ./bin
./configure --prefix=/tmp/libfabric/bin
make && make install
export PATH=$PATH:/tmp/libfabric/bin/bin
```

Note that with the daemonset, you should see efa as an option:

```bash
./efa_test.sh
```
```console
provider: efa
    fabric: efa
    domain: rdmap0s31-rdm
    version: 120.0
    type: FI_EP_RDM
    protocol: FI_PROTO_EFA
provider: efa
    fabric: efa
    domain: rdmap0s31-dgrm
    version: 120.0
    type: FI_EP_DGRAM
    protocol: FI_PROTO_EFA
```

And you should be able to run tests.

```bash
cd /tmp/efa/efa
/tmp/efa/aws-efa-installer
./efa_test.sh
```
```console
Localhost fi_pingpong test: Attempt 1 (max 3)...
Starting server...
Starting client...
Server Log:
bytes   #sent   #ack     total       time     MB/sec    usec/xfer   Mxfers/sec
64      10      =10      1.2k        0.02s      0.08     803.40       0.00
256     10      =10      5k          0.00s     30.66       8.35       0.12
1k      10      =10      20k         0.00s    128.00       8.00       0.12
4k      10      =10      80k         0.00s    490.54       8.35       0.12
64k     10      =10      1.2m        0.00s   4566.97      14.35       0.07
1m      10      =10      20m         0.00s  15397.59      68.10       0.01
Client Log:
bytes   #sent   #ack     total       time     MB/sec    usec/xfer   Mxfers/sec
64      10      =10      1.2k        0.02s      0.08     803.75       0.00
256     10      =10      5k          0.00s     29.60       8.65       0.12
1k      10      =10      20k         0.00s    123.37       8.30       0.12
4k      10      =10      80k         0.00s    476.28       8.60       0.12
64k     10      =10      1.2m        0.00s   4664.48      14.05       0.07
1m      10      =10      20m         0.00s  15500.01      67.65       0.01
fi_pingpong: SUCCESS!
```
