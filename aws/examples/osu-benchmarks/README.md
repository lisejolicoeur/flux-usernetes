# OSU Benchmarks
  
Let's again compare bare metal to usernetes

1. run on bare metal with lammps + flux
2. run on bare metal with lammps in container + flux
3. run in usernetes with same container and lammps
4. run on bare metal (with and without container) but with usernetes running (to assess overhead)
 
```bash
docker build -t ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04 .
docker push ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04
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

For the set, I'm going to stick with what we [decided before](https://github.com/converged-computing/metrics-operator-experiments/blob/main/google/kubecon/osu-benchmarks/run6/crd/metrics-64.yaml):

- osu_allreduce
- osu_barrier
- osu_latency

These are installed to the host, at the same version as in the container.

```bash
# 25 seconds 
binary=/usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce
time flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task $binary
# 11 seconds
time flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task $binary
# 5 seconds
time flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task $binary

# 8 seconds
binary=/usr/local/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency
time flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task $binary

# 2 seconds each
binary=/usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier
time flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task $binary
time flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task $binary
time flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task $binary
```

How to run across sizes:

```bash
screen /bin/bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal/all_reduce-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal/all_reduce-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal/all_reduce-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal/all_reduce-4-64-${i}.out

    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal/osu_barrier-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal/osu_barrier-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal/osu_barrier-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal/osu_barrier-4-64-${i}.out

    flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency  |& tee ./results/bare-metal/osu_latency-${i}.out
done
```

### 2. Container LAMMPS with Flux

Note that the container is built from [docker](docker).

```bash
flux exec --rank all mkdir -p /home/ubuntu/osu
cd /home/ubuntu/osu
flux exec --rank all --dir /home/ubuntu/osu singularity pull docker://ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04
container=/home/ubuntu/osu/osu-benchmarks-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container

# Test runs

# 8 seconds
time flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce
# 5 seconds
time flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce
# 4 seconds
time flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce

# 8 seconds
time flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task singularity exec $container osu_latency

# ~2.5 seconds each
time flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier
time flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier
time flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier
```
Now the experiment loop again
```
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container/all_reduce-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container/all_reduce-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container/all_reduce-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container/all_reduce-4-64-${i}.out

    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container/osu_barrier-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container/osu_barrier-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container/osu_barrier-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container/osu_barrier-4-64-${i}.out

    flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task singularity exec $container osu_latency  |& tee ./results/container/osu_latency-${i}.out
done
```

### 3. Flux Operator with Lammps

This comes down to installing the operator and submitting the same job with usernetes. You should already have usernetes setup per instructions in the top level aws README. Note that we are going to be using version 2 (refactor) of the Flux Operator. After you have the control plane and all kubelets running, let's install it.

```bash
# Autocomplete
source <(kubectl completion bash) 

# Sanity check your cluster is there...
kubectl get nodes
```

We are going to install the efa plugin (terribly tweaked by me to get it working...) and the Flux Operator, pinned to a specific release for ARM. You should have already cloned into the lammps experiment, and you might have already done these steps.

```bash
kubectl apply -f ../lammps/flux-usernetes/aws/examples/lammps/crd/efa-device-plugin.yaml 
kubectl apply -f ../lammps/flux-usernetes/aws/examples/lammps/crd/flux-operator-arm.yaml

# Make sure it's running
kubectl logs -n operator-system operator-controller-manager-547869d677-8pqmt 

# Copy the crd file
cp -R ../lammps/flux-usernetes/aws/examples/osu-benchmarks/crd ./crd
```

Now let's run the experiments in Usernetes. For each minicluster, you'll need to tweak the size.

```bash
# Create output directory for results
mkdir -p ./results/usernetes

# Run once to pull containers to nodes (this will be thrown away)
kubectl apply -f ./crd/minicluster-efa-all-reduce.yaml
kubectl apply -f ./crd/minicluster-efa-barrer.yaml
kubectl apply -f ./crd/minicluster-efa-osu-latency.yaml

# Test these commands before running in loop
pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)

# This will stream until it finishes
echo "Lead broker pod is ${pod}"
kubectl logs ${pod} -f |& tee /tmp/test.out

# And this absolutely waits until the job is deemed complete
kubectl wait --for=condition=complete job/flux-sample
kubectl delete -f ./minicluster-efa.yaml --wait=true
```

I think for this experiment I'll run in the loop, and do for each of the sizes, changing the config and output file appropriately.
Here are the estimated times.

- all_reduce
  - size 8: 100 seconds
  - size 4: 50 seconds
  - size 2: 55 seconds

- barrier:
  - size 8: 30 seconds
  - size 4: 30 seconds
  - size 2: 30 seconds
  
- latency
  - 35 seconds
  
```bash
# Do this for each size 4, 8, 16, 32
# YOU WILL NEED TO CHANGE THE SIZE IN THE MINICLUSTERS YAML FILES
size=32
for i in $(seq 1 20); do 
    echo "Running iteration ${i}"

    kubectl apply -f ./crd/minicluster-efa-all-reduce.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    # Wait for init to finish and pod to initialize
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    # This waits for lammps to finish (streaming the log)
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-all-reduce-${size}-${i}.out
    # And an extra precaution the entire job/workers are complete
    kubectl wait --for=condition=complete --timeout=120s job/flux-sample-efa
    kubectl delete -f ./crd/minicluster-efa-all-reduce.yaml 

    kubectl apply -f ./crd/minicluster-efa-barrier.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    # Wait for init to finish and pod to initialize
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    # This waits for lammps to finish (streaming the log)
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-barrier-${size}-${i}.out
    # And an extra precaution the entire job/workers are complete
    kubectl wait --for=condition=complete --timeout=120s job/flux-sample-efa
    kubectl delete -f ./crd/minicluster-efa-barrier.yaml

    kubectl apply -f ./crd/minicluster-efa-osu-latency.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    # Wait for init to finish and pod to initialize
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    # This waits for lammps to finish (streaming the log)
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-latency-${size}-${i}.out
    # And an extra precaution the entire job/workers are complete
    kubectl wait --for=condition=complete --timeout=120s job/flux-sample-efa
    kubectl delete -f ./crd/minicluster-efa-osu-latency.yaml
done
```

And then you are done! Copy the data, or you will be very sad.
