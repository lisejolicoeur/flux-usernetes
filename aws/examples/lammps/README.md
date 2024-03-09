# MPI Application with LAMMPS
  
We want to look at the following four cases:

1. run on bare metal with lammps + flux
2. run on bare metal with lammps in container + flux
3. run in usernetes with same container and lammps
4. run on bare metal (with and without container) but with usernetes running (to assess overhead)

We are going to use our [tf setup](../tf) on (still) a small node type, but with 7 instances.

- Using 6 nodes on a 7 node cluster
- Problem size 32 x 8 x 16
- index 0 (control plane and flux lead broker) will not run jobs.
 
### Why are we looking at the four cases above?

We expect to see that using usernetes is slower, and this would make sense because of the networking. Thus, we would want to say "with this setup you can get the best of both worlds - running your HPC apps (e.g., lammps) directly on the cluster, and then associated services alongside." The reason for having the lammps container vs. on bare metal is to demonstrate the transition between the three cases:

```console
[bare metal with flux] -> [container with flux] -> [usernetes with flux]
```

In our Star Trek cluster experiments (presented at FOSDEM) we found that usernetes was twice as slow.
Note that for the above you will need to start the control plane and workers (connect) for each node.

## Build Container

The container in [docker](docker) is built to match the host. On the same host, do:

```bash
docker build -t ghcr.io/rse-ops/lammps-efa:ubuntu-22.04 .
docker push ghcr.io/rse-ops/lammps-efa:ubuntu-22.04
```

## Run Experiments

We should have efa:

```
fi_info | less
```
```console
provider: efa
    fabric: efa
    domain: rdmap0s31-rdm
    version: 119.0
    type: FI_EP_RDM
    protocol: FI_PROTO_EFA
provider: efa
    fabric: efa
    domain: rdmap0s31-dgrm
    version: 119.0
    type: FI_EP_DGRAM
    protocol: FI_PROTO_EFA
...
```

Note that I found [this cheat sheet](https://github.com/aws/aws-ofi-nccl/blob/master/doc/efa-env-var.md) helpful.
Ultimately I didn't need to set any envars - it just seemed to work.

### 1. Bare Metal LAMMPS with Flux

You'll need to first shell into your control plane. You should see flux running and usernetes.

```bash
flux resource list
kubectl get nodes
```

Let's make results directories, etc.

```bash
# This is where the example is
cd /home/ubuntu/lammps

# Create output directory for results
mkdir -p ./results/bare-metal
```

#### Testing commands

This should work.  I'm not actually sure if we need any of these extra envars, but I think not? I'll leave them here for record. You can add one to flux like `--env=FI_PROVIDER=efa`

```bash
flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 2 -v y 2 -v z 2 -in ./in.reaxff.hns -nocite
```

Try a bigger problem size:

```bash
flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 8 -v y 8 -v z 8 -in ./in.reaxff.hns -nocite
```

That took about 45 seconds, seems ok. One thing I'm not sure about is how to ensure we are using EFA - I assume because it wasn't working before (and we saw errors with libfabric) we are using it now. I am not using these, but want to keep them here for future Googling. Note that I also learned today that after version 1.20, libfabric on GitHub is mostly equivalent to the AWS efa installer.

```console
# Likely not needed?
FI_LOG_LEVEL=debug
FI_EFA_USE_DEVICE_RDMA=1
FI_EFA_USE_HUGE_PAGE=0
FI_PROVIDER=efa
NCCL_PROTO=simple
FI_EFA_ENABLE_SHM_TRANSFER=0
```

Here is how to do the runs:

```bash
screen /bin/bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 8 -v y 8 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-${i}.out
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

**NOTE: this needs to be done on a larger sized cluster to test across nodes*

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

We are going to install the efa plugin (terribly tweaked by me to get it working...)

```bash
kubectl apply -f crd/efa-device-plugin.yaml
```

Let's get the lammps configuration - it's in this repository [crd/minicluster-efa.yaml](crd/minicluster-efa.yaml)
First do a setup and test run:

```bash
# Create output directory for results
mkdir -p ./results/usernetes

# Run once to pull containers to nodes (this will be thrown away)
kubectl apply -f crd/minicluster-efa.yaml

# Test these commands before running in loop
pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)

# This will stream until it finishes
echo "Lead broker pod is ${pod}"
kubectl logs ${pod} -f |& tee /tmp/test.out

# And this absolutely waits until the job is deemed complete
kubectl wait --for=condition=complete job/flux-sample
kubectl delete -f crd/minicluster-efa.yaml --wait=true
```

**Note: I have not run this yet - it's slower and I need to calculate time/cost for a given set of cluster sizes**

Note that you can use `kubectl get pods -o wide` to see the nodes assigned to each pod (it should be 1:1), and you won't see anything assigned on the control plane, which isn't necessarily the index 0 pod, but is always the index 0 node! When you are happy, loopize it:

```bash
for i in $(seq 1 20); do 
    echo "Running iteration ${i}"
    kubectl apply -f ./crd/minicluster-efa.yaml 
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
    kubectl delete -f /crd/minicluster-efa.yaml --wait=true
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
