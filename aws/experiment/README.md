# Flux Usernetes Experiment on AWS

Note that we re-did the osu all reduce on 2 nodes in [final/osu-followup](final/osu-followup)

### Lammps and OSU Benchmarks

- Start time: 6:35 am, May 28, 2024
- End time:  4:20pm 
- hpc7g.4xlarge x 33
- Estimated compute cost: $56 per hour.

$1.70 * 33 * 13 hours 24 minutes.

```bash
     STATE NNODES   NCORES    NGPUS NODELIST
      free     33      528        0 i-025dbde9417bb3475,i-09124ea65570893e1,i-00d031d7d0229f067,i-0f918aa45d74423dc,i-0b0bffe6cfdddf1e0,i-0051360b6972b9793,i-0a9e61f51088d629a,i-096d773b3c1c4865b,i-07e72f800aeac91ee,i-072271fb5d87f13ff,i-032d81636b0368b02,i-0ed9701caad786099,i-08034e7752f4ff06b,i-062f6ef897a2d348a,i-0de1b95852bf44467,i-0100ff6d7226dc37d,i-010a805233309a84c,i-05155a38136e76e2d,i-0dba099e5c631312c,i-00f9aa65f556f02d9,i-05d44ce89b17319b8,i-0ed0106fa11d111f5,i-096fc591e9e10c920,i-0db82f08286a82a70,i-09f620a14a17920e6,i-0771fe5fdc1fc8406,i-0a44a5332b1d7dfc4,i-062288504aa3d1887,i-06d3c1ae7993992b9,i-0b1466cde74e550a9,i-05371ba854ad08db1,i-05c66519131b8cd62,i-0582c6de931684c30
 allocated      0        0        0 
      down      0        0        0 
```

Topology for later:

```bash
aws ec2 describe-instance-topology --region us-east-1 --filters Name=instance-type,Values=hpc7g.4xlarge > topology-33.json
aws ec2 describe-instances --filters "Name=instance-type,Values=hpc7g.4xlarge" --region us-east-1 > instances-33.json
```

## LAMMPS

```bash
cd /home/ubuntu/lammps
mkdir -p ./results/bare-metal
```

Runs across sizes for each of the following:

- 32, 512
- 16, 256
- 8, 128
- 4, 64

```console
screen /bin/bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-4-64-${i}.out
done
```

Now container runs for lammps. This container should already be on the system.

```bash
cd /home/ubuntu/lammps
flux exec --rank all --dir /home/ubuntu/lammps singularity pull docker://ghcr.io/rse-ops/lammps-efa:ubuntu-22.04
container=/home/ubuntu/lammps/lammps-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container
```

And the experiments!

```console
# Run the same loop, but in the container
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container/lammps-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container/lammps-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container/lammps-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container/lammps-4-64-${i}.out
done
```

You can sanity check each of the above as you go - there should be 80 files in each directory.
Now we are going to switch over the osu to run on bare metal, before we start usernetes.

```bash
# This is where the example is
flux exec --rank all mkdir -p /home/ubuntu/osu
cd /home/ubuntu/osu

# Create output directory for results
mkdir -p ./results/bare-metal
flux exec --rank all -x 0 mkdir -p /home/ubuntu/osu
```

And run the experiments:

```bash
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

Now let's run the same OSU benchmarks with a container.

```bash
flux exec --rank all --dir /home/ubuntu/osu singularity pull docker://ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04
container=/home/ubuntu/osu/osu-benchmarks-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container
```

Now the experiment loop again

```console
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

Now we've finished running lammps on bare metal (with and without containers) and the same for OSU (with and without containers) we can bring up usernetes to run lammps and osu there.

```bash
cd ~/usernetes
./start-control-plane.sh
```

Then with flux running, send to the other nodes.

```bash
# use these commands for newer flux
flux archive create --name=join-command --mmap -C /home/ubuntu/usernetes join-command
flux exec -x 0 -r all flux archive extract --name=join-command -C /home/ubuntu/usernetes
```

Note that I'm going to try a command that will be able to start the workers without needing to shell in.

```bash
flux exec -x 0 -r all --dir /home/ubuntu/usernetes /bin/bash ./start-worker.sh
```

I sourced my bash profile and then ensured I had my nodes, and saved them too.

```bash
. ~/.bashrc
kubectl get nodes
```
```console
NAME                      STATUS   ROLES           AGE    VERSION
u7s-i-0051360b6972b9793   Ready    <none>          31s    v1.29.1
u7s-i-00d031d7d0229f067   Ready    <none>          31s    v1.29.1
u7s-i-00f9aa65f556f02d9   Ready    <none>          31s    v1.29.1
u7s-i-0100ff6d7226dc37d   Ready    <none>          31s    v1.29.1
u7s-i-010a805233309a84c   Ready    <none>          31s    v1.29.1
u7s-i-025dbde9417bb3475   Ready    control-plane   2m6s   v1.29.1
u7s-i-032d81636b0368b02   Ready    <none>          31s    v1.29.1
u7s-i-05155a38136e76e2d   Ready    <none>          31s    v1.29.1
u7s-i-05371ba854ad08db1   Ready    <none>          30s    v1.29.1
u7s-i-0582c6de931684c30   Ready    <none>          31s    v1.29.1
u7s-i-05c66519131b8cd62   Ready    <none>          31s    v1.29.1
u7s-i-05d44ce89b17319b8   Ready    <none>          31s    v1.29.1
u7s-i-062288504aa3d1887   Ready    <none>          31s    v1.29.1
u7s-i-062f6ef897a2d348a   Ready    <none>          31s    v1.29.1
u7s-i-06d3c1ae7993992b9   Ready    <none>          31s    v1.29.1
u7s-i-072271fb5d87f13ff   Ready    <none>          32s    v1.29.1
u7s-i-0771fe5fdc1fc8406   Ready    <none>          22s    v1.29.1
u7s-i-07e72f800aeac91ee   Ready    <none>          31s    v1.29.1
u7s-i-08034e7752f4ff06b   Ready    <none>          31s    v1.29.1
u7s-i-09124ea65570893e1   Ready    <none>          31s    v1.29.1
u7s-i-096d773b3c1c4865b   Ready    <none>          30s    v1.29.1
u7s-i-096fc591e9e10c920   Ready    <none>          30s    v1.29.1
u7s-i-09f620a14a17920e6   Ready    <none>          30s    v1.29.1
u7s-i-0a44a5332b1d7dfc4   Ready    <none>          31s    v1.29.1
u7s-i-0a9e61f51088d629a   Ready    <none>          32s    v1.29.1
u7s-i-0b0bffe6cfdddf1e0   Ready    <none>          31s    v1.29.1
u7s-i-0b1466cde74e550a9   Ready    <none>          31s    v1.29.1
u7s-i-0db82f08286a82a70   Ready    <none>          31s    v1.29.1
u7s-i-0dba099e5c631312c   Ready    <none>          31s    v1.29.1
u7s-i-0de1b95852bf44467   Ready    <none>          31s    v1.29.1
u7s-i-0ed0106fa11d111f5   Ready    <none>          31s    v1.29.1
u7s-i-0ed9701caad786099   Ready    <none>          30s    v1.29.1
u7s-i-0f918aa45d74423dc   Ready    <none>          31s    v1.29.1
```
```bash
kubectl get nodes -o json > ../osu/results/nodes-33.json
```

Now let's prepare the operator.


```bash
# Autocomplete
source <(kubectl completion bash) 
```

Clone the repository with configs, etc.

```bash
git clone -b add-experiment-march-10 https://github.com/converged-computing/flux-usernetes /home/ubuntu/lammps/flux-usernetes

# This is run from /home/ubuntu/lammps
kubectl apply -f ./flux-usernetes/aws/examples/lammps/crd/efa-device-plugin.yaml 
kubectl apply -f ./flux-usernetes/aws/examples/lammps/crd/flux-operator-arm.yaml

# Make sure it's running
kubectl logs -n operator-system operator-controller-manager-547869d677-8pqmt 
```

```console
cp flux-usernetes/aws/examples/lammps/crd/minicluster-efa.yaml .
# vim minicluster-efa.yaml
```

Prepare to run.

```bash
# Create output directory for results
mkdir -p ./results/usernetes
```

Change to full size and run once to pull containers (so our actual runs don't need to do that)

```bash
# Run once to pull containers to nodes (this will be thrown away)
kubectl apply -f ./minicluster-efa.yaml
kubectl delete -f ./minicluster-efa.yaml
```

Note that I did `kubectl get pods -o wide` to sanity check we had an assignment of one pod per node (we did)!
Now we will need to run for each size mentioned in the experiment file:

```
# sizes for experiment:
# 32, 512
# 16, 256
# 8, 128
# 4, 64
```

To be clear, you need to change the size in the minicluster-efa.yaml for each of the above, coordinated with the loop below (which is saving the result to that path).

```bash
size=4
tasks=64
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
    kubectl logs ${pod} -f |& tee ./results/usernetes/lammps-${size}-${tasks}-${i}.out
    # And an extra precaution the entire job/workers are complete
    kubectl wait --for=condition=complete --timeout=120s job/flux-sample-efa
    kubectl delete -f ./minicluster-efa.yaml --wait=true
done
```

Now let's run the benchmarks in kubernetes (usernetes).


```console
cd /home/ubuntu/osu
cp -R ../lammps/flux-usernetes/aws/examples/osu-benchmarks/crd ./crd
```

Now let's run the experiments in Usernetes. For each minicluster, you'll need to tweak the size,
but the experiments (barrier, allreduce, etc) are provided separately.

```bash
# Create output directory for results
mkdir -p ./results/usernetes

# Run one to pull the container to all nodes
kubectl apply -f ./crd/minicluster-efa-all-reduce.yaml
kubectl delete -f ./crd/minicluster-efa-all-reduce.yaml
```

```bash
# Do this for each size 32, 16, 8, and 4 (it gets faster)
# YOU WILL NEED TO CHANGE THE SIZE IN THE MINICLUSTERS YAML FILES
# Note that we can comment out the last section (latency) after the first 20 runs.
size=4
for i in $(seq 1 20); do 
    echo "Running iteration ${i}"
    kubectl apply -f ./crd/minicluster-efa-all-reduce.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-all-reduce-${size}-${i}.out
    kubectl delete -f ./crd/minicluster-efa-all-reduce.yaml 

    kubectl apply -f ./crd/minicluster-efa-barrier.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-barrier-${size}-${i}.out
    kubectl delete -f ./crd/minicluster-efa-barrier.yaml

    kubectl apply -f ./crd/minicluster-efa-osu-latency.yaml
    sleep 10
    pod=$(kubectl get pods -o json | jq -r .items[0].metadata.name)
    echo "Lead broker pod is ${pod}"
    kubectl wait --for=condition=ready --timeout=120s pod/${pod}
    sleep 10
    kubectl logs ${pod} -f |& tee ./results/usernetes/osu-latency-${size}-${i}.out
    kubectl delete -f ./crd/minicluster-efa-osu-latency.yaml
done
```

After this, we go back and run the initial bare metal runs again, for lammps and osu benchmarks. The difference is that we have usernetes running in the background.

```bash
cd /home/ubuntu/lammps
mkdir -p ./results/bare-metal-with-usernetes
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal-with-usernetes/lammps-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal-with-usernetes/lammps-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal-with-usernetes/lammps-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal-with-usernetes/lammps-4-64-${i}.out
done
```

Now container runs for lammps.

```bash
container=/home/ubuntu/lammps/lammps-efa_ubuntu-22.04.sif
mkdir -p ./results/container-with-usernetes

# Run the same loop, but in the container
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container-with-usernetes/lammps-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container-with-usernetes/lammps-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container-with-usernetes/lammps-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/container-with-usernetes/lammps-4-64-${i}.out
done
```

Do the same for OSU, on bare metal, with and without a container.

```bash
cd /home/ubuntu/osu
mkdir -p ./results/bare-metal-with-usernetes
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal-with-usernetes/all_reduce-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal-with-usernetes/all_reduce-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal-with-usernetes/all_reduce-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal-with-usernetes/all_reduce-4-64-${i}.out
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal-with-usernetes/osu_barrier-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal-with-usernetes/osu_barrier-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal-with-usernetes/osu_barrier-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_barrier  |& tee ./results/bare-metal-with-usernetes/osu_barrier-4-64-${i}.out
    flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/pt2pt/osu_latency  |& tee ./results/bare-metal-with-usernetes/osu_latency-${i}.out
done
```

Now let's run the same OSU benchmarks with a container.

```bash
container=/home/ubuntu/osu/osu-benchmarks-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container-with-usernetes
```

Now the experiment loop again

```console
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container-with-usernetes/all_reduce-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container-with-usernetes/all_reduce-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container-with-usernetes/all_reduce-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container-with-usernetes/all_reduce-4-64-${i}.out
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container-with-usernetes/osu_barrier-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container-with-usernetes/osu_barrier-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container-with-usernetes/osu_barrier-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task singularity exec $container osu_barrier  |& tee ./results/container-with-usernetes/osu_barrier-4-64-${i}.out
    flux run -N 2 --ntasks 2 -c 1 -o cpu-affinity=per-task singularity exec $container osu_latency  |& tee ./results/container-with-usernetes/osu_latency-${i}.out
done
```


And then you are done! Copy the data, or you will be very sad. I did this at several increments, mostly worried about losing data.
And some extra flux info:

```
$ flux resource info
33 Nodes, 528 Cores, 0 GPUs
ubuntu@i-09b9c39571c635328:~$ flux resource R
{"version": 1, "execution": {"R_lite": [{"rank": "0-32", "children": {"core": "0-15"}}], "starttime": 0.0, "expiration": 0.0, "nodelist": ["i-025dbde9417bb3475,i-09124ea65570893e1,i-00d031d7d0229f067,i-0f918aa45d74423dc,i-0b0bffe6cfdddf1e0,i-0051360b6972b9793,i-0a9e61f51088d629a,i-096d773b3c1c4865b,i-07e72f800aeac91ee,i-072271fb5d87f13ff,i-032d81636b0368b02,i-0ed9701caad786099,i-08034e7752f4ff06b,i-062f6ef897a2d348a,i-0de1b95852bf44467,i-0100ff6d7226dc37d,i-010a805233309a84c,i-05155a38136e76e2d,i-0dba099e5c631312c,i-00f9aa65f556f02d9,i-05d44ce89b17319b8,i-0ed0106fa11d111f5,i-096fc591e9e10c920,i-0db82f08286a82a70,i-09f620a14a17920e6,i-0771fe5fdc1fc8406,i-0a44a5332b1d7dfc4,i-062288504aa3d1887,i-06d3c1ae7993992b9,i-0b1466cde74e550a9,i-05371ba854ad08db1,i-05c66519131b8cd62,i-0582c6de931684c30"]}}
```

To plot results for LAMMPS

```bash
python plot-lammps.py
```
```console
                           ranks iteration time_seconds  nodes percent_cpu_utilization
experiment                                                                            
bare-metal                 240.0      10.5         41.8   15.0                   99.65
bare-metal-with-usernetes  240.0      10.5       42.625   15.0                99.46875
container                  240.0      10.5       42.225   15.0                99.65125
container-with-usernetes   240.0      10.5      42.7375   15.0                99.46375
usernetes                  240.0      10.5       128.05   15.0                    43.7
                                ranks  iteration  time_seconds      nodes  percent_cpu_utilization
experiment                                                                                        
bare-metal                 172.663425   5.802662     25.978764  10.791464                 0.111378
bare-metal-with-usernetes  172.663425   5.802662     25.475913  10.791464                 0.110915
container                  172.663425   5.802662     25.573411  10.791464                 0.110228
container-with-usernetes   172.663425   5.802662     25.492488  10.791464                 0.110515
usernetes                  172.663425   5.802662     62.431715  10.791464                 0.000000
```

### Machine Learning Hybrid Example

Bring up the main.tf with:

 - size 5 nodes for a size 4 cluster (we don't need any kind of scale here to demonstrate it working).
 
```bash
cd ~/usernetes
```

Update the docker-compose.yaml

```console
wget -O docker-compose-ml.yaml https://raw.githubusercontent.com/converged-computing/flux-usernetes/main/aws/examples/ml-server/crd/docker-compose.yaml
flux archive create --name=docker-compose --mmap -C /home/ubuntu/usernetes docker-compose-ml.yaml
flux exec -x 0 -r all flux archive extract --name=docker-compose -C /home/ubuntu/usernetes
flux exec -r all --dir /home/ubuntu/usernetes mv docker-compose-ml.yaml docker-compose.yaml
```

And then start usernetes, the control plane then workers (from the control plane, nice)!

```bash
./start-control-plane.sh
flux archive create --name=join-command --mmap -C /home/ubuntu/usernetes join-command
flux exec -x 0 -r all flux archive extract --name=join-command -C /home/ubuntu/usernetes
flux exec -x 0 -r all --dir /home/ubuntu/usernetes /bin/bash ./start-worker.sh
. ~/.bashrc
kubectl get nodes

# Autocomplete
source <(kubectl completion bash) 
```

Deploy the machine learning server.

```bash
cd /home/ubuntu/lammps
kubectl  apply -f flux-usernetes/aws/examples/ml-server/crd/server-deployment.yaml
```

This is how to get the host:

```bash
kubectl  get pods -o wide
```
```console
NAME                         READY   STATUS    RESTARTS   AGE     IP           NODE                      NOMINATED NODE   READINESS GATES
ml-server-6547db94fd-qjwkb   1/1     Running   0          6m32s   10.244.1.5   u7s-i-0ba186b66890a2230   <none>           <none>
```
```bash
host=http://i-0be4941438656344d:8080
curl -k $host/api/ | jq
```
```console
{
  "id": "django_river_ml",
  "status": "running",
  "name": "Django River ML Endpoint",
  "description": "This service provides an api for models",
  "documentationUrl": "https://vsoch.github.io/django-river-ml",
  "storage": "shelve",
  "river_version": "0.21.0",
  "version": "0.0.21"
}
```

Create three empty models, different kinds of regressions. This is container that has river packaged we can use as a client.

```bash
flux exec -r all --dir /home/ubuntu/lammps singularity pull docker://ghcr.io/converged-computing/lammps-stream-ml:lammps-arm
```

Here is how to create the models for the running server. The names will be funny but largely don't matter - we can get them programmatically later.

```bash
# Remember, we need to run this from the lammps root!
cd /home/ubuntu/lammps

# Set the container path
container=/home/ubuntu/lammps/lammps-stream-ml_lammps-arm.sif

# Install the riverapi for local interaction
python3 -m pip install riverapi 

# the host should be set in the environment, $host
echo $host

# Assumes service running on localhost directory (first parameter, default)
singularity exec $container python3 /code/1-create-models.py $host
```
```console
Preparing to create models for client URL http://i-0c79705f628c562a3:8080
Created model expressive-cupcake
Created model confused-underoos
Created model doopy-platanos
```

### Train lammps

Copy the script into the lammps directory, for easy access.

```bash
cp ./flux-usernetes/aws/examples/ml-server/docker/scripts/2-run-lammps-flux.py .
```

Run jobs with flux (train), 1000 samples, for 4 nodes and up to 8x8x8.

```bash
# screen so we don't lose stuff
screen /bin/bash
time python3 2-run-lammps-flux.py train --container $container --np 64 --nodes 4 --workdir /opt/lammps/examples/reaxff/HNS --x-min 1 --x-max 8 --y-min 1 --y-max 8 --z-min 1 --z-max 8 --iters 1000 --url $host
```

Note that training took 146 minutes:

```console
  Training quirky-rabbit with {'x': 8, 'y': 3, 'z': 2} to predict 4
  Training swampy-knife with {'x': 8, 'y': 3, 'z': 2} to predict 4

real    146m11.027s
user    1m34.516s
sys     0m20.570s
```

### Predict LAMMPS

Now let's generate more data, but this time, compare the actual time with each model prediction. This script is very similar but calls a different API function.

```bash
python3 2-run-lammps-flux.py predict --container $container --np 64 --nodes 4 --workdir /opt/lammps/examples/reaxff/HNS --x-min 1 --x-max 8 --y-min 1 --y-max 8 --z-min 1 --z-max 8 --iters 250 --url $host --out test-predict.json
```
```console
🧪️ Running iteration 0
/usr/bin/mpirun -N 1 --ppn 4 /usr/bin/lmp -v x 5 y 5 z 7 -log /tmp/lammps.log -in in.reaxc.hns -nocite
  Predicted value for confused-underoos with {'x': 5, 'y': 5, 'z': 7} is 29.434425573805264
  Predicted value for doopy-platanos with {'x': 5, 'y': 5, 'z': 7} is 45.12076412968298
  Predicted value for expressive-cupcake with {'x': 5, 'y': 5, 'z': 7} is 23.273189928153677

🧪️ Running iteration 1
/usr/bin/mpirun -N 1 --ppn 4 /usr/bin/lmp -v x 6 y 3 z 3 -log /tmp/lammps.log -in in.reaxc.hns -nocite
  Predicted value for confused-underoos with {'x': 3, 'y': 3, 'z': 3} is 14.937652338729954
  Predicted value for doopy-platanos with {'x': 3, 'y': 3, 'z': 3} is 24.11752143485609
  Predicted value for expressive-cupcake with {'x': 3, 'y': 3, 'z': 3} is 20.551130455244824

🧪️ Running iteration 2
/usr/bin/mpirun -N 1 --ppn 4 /usr/bin/lmp -v x 1 y 5 z 8 -log /tmp/lammps.log -in in.reaxc.hns -nocite
  Predicted value for confused-underoos with {'x': 5, 'y': 5, 'z': 8} is 31.7035947450996
  Predicted value for doopy-platanos with {'x': 5, 'y': 5, 'z': 8} is 47.583211665477734
  Predicted value for expressive-cupcake with {'x': 5, 'y': 5, 'z': 8} is 23.48086378670319
```

And then you'll run lammps for some number of iterations (defaults to 20) and calculate an metrics for each model.
Note that there are a lot of metrics you can see [here](https://riverml.xyz/latest/api/metrics/Accuracy/) (that's just a link to the first). The server itself also stores basic metrics, but we are doing this manually so it's a hold out test set.
Yes, these are quite bad, but it was only 20x for runs.

```console
ammps-arm.sif /usr/bin/lmp -v x 7 -v y 3 -v z 8 -log /tmp/lammps.log -in in.reaxff.hns -nocite
       result => Lammps run took 10 seconds
Model grated-ricecake predicts 11.04232057784137
Model quirky-rabbit predicts 16.345048556969655
Model swampy-knife predicts 8.781309553686834

⭐️ Performance for: grated-ricecake
          R Squared Error: 0.7918090116097876
       Mean Squared Error: 4.185888012573615
      Mean Absolute Error: 1.5499159478805307
  Root Mean Squared Error: 2.0459442838390336

⭐️ Performance for: quirky-rabbit
          R Squared Error: -0.5642529044232998
       Mean Squared Error: 31.450868896334878
      Mean Absolute Error: 5.189548235918719
  Root Mean Squared Error: 5.608107425534471

⭐️ Performance for: swampy-knife
          R Squared Error: 0.6045018869230796
       Mean Squared Error: 7.951885061524557
      Mean Absolute Error: 2.2032914541509716
  Root Mean Squared Error: 2.8199086973738274
```

Negative R squared, lol. 😬️ Let's save our models.


```bash
mkdir -p out
cd out
```
```python
from riverapi.main import Client

cli = Client('http://i-0be4941438656344d:8080')

# Download model as pickle
for model_name in cli.models()['models']:
    # Saves to model-name>.pkl in pwd unless you provide a second arg, dest
    cli.download_model(model_name)

# Also save metrics and stats
import json
results = {}
for model_name in cli.models()['models']:
    results[model_name] = {
        "model": cli.get_model_json(model_name),
        "stats": cli.stats(model_name),
        "metrics": cli.metrics(model_name)
    } 

with open('post-train-models.json', 'w') as fd:
    fd.write(json.dumps(results, indent=3))
```

