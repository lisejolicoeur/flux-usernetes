# Flux Usernetes Experiment on AWS

- Start time: 10:29 am, March 10 2024
- End time: 11:53pm
- hpc7g.4xlarge x 33
- Estimated compute cost $1.70 * 33 * 13 hours 24 minutes.

```bash
     STATE NNODES   NCORES    NGPUS NODELIST
      free     33      528        0 i-09b9c39571c635328,i-008f0e304d40ca3a2,i-028d109545c7334f8,i-06e26186f161a497a,i-0d44943116b931622,i-0742dc17f9707ecd4,i-0a3cb311d11f5b22a,i-0092e145bacacbb50,i-01ae08da1fefbbc5a,i-0544124d44f45121f,i-0477541c56fbf8333,i-00a6e26c9695fe255,i-06d868abf3f33f852,i-08751f901b3d8cd91,i-02d69237f31355786,i-09425b966ee3c9530,i-09da2dea953dd1bed,i-06ed29b5f2be73029,i-029e274e9c87e92ee,i-0012875cd3aabf5c6,i-020ce554596630f85,i-0a1047f24d3f30c9f,i-0889c960423636da3,i-0a458abb18af676e8,i-09a42753c5b24aa78,i-0997f355da1326bc1,i-024f98dea1d5390a1,i-022ead1bb3f3cfd88,i-08d11416273066ef9,i-02fda578dbaeb41c5,i-0a2a4357b398e5531,i-01d328f0112b6bca5,i-04d7fa1b8f3897468
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

```bash
screen /bin/bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 32 --ntasks 512 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-32-512-${i}.out
    flux run -N 16 --ntasks 256 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-16-256-${i}.out
    flux run -N 8 --ntasks 128 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-8-128-${i}.out
    flux run -N 4 --ntasks 64 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 16 -v y 16 -v z 8 -in ./in.reaxff.hns -nocite |& tee ./results/bare-metal/lammps-4-64-${i}.out
done
```

Now container runs for lammps.

```bash
cd /home/ubuntu/lammps
flux exec --rank all --dir /home/ubuntu/lammps singularity pull docker://ghcr.io/rse-ops/lammps-efa:ubuntu-22.04
container=/home/ubuntu/lammps/lammps-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container
```

And the experiments!

```
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

```
. ~/.bashrc
kubectl get nodes
kubectl get nodes -o json > ../osu/results/nodes-33.json
```

Now let's prepare the operator.


```bash
# Autocomplete
source <(kubectl completion bash) 
```

Clone the repository with configs, etc.

```bash
git clone https://github.com/converged-computing/flux-usernetes /home/ubuntu/lammps/flux-usernetes

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

Now we will need to run for each size mentioned in the experiment file:

```
# sizes for experiment:
# 32, 512
# 16, 256
# 8, 128
# 4, 64
```

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

After this, we go back and run the initial bare metal runs again, for lammps and osu benchmarks. The difference is that we have usernestes running in the background.

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

```console
scp -r -i ~/.ssh/dinosaur-llnl
```

And some extra flux info:

```
$ flux resource info
33 Nodes, 528 Cores, 0 GPUs
ubuntu@i-09b9c39571c635328:~$ flux resource R
{"version": 1, "execution": {"R_lite": [{"rank": "0-32", "children": {"core": "0-15"}}], "starttime": 0.0, "expiration": 0.0, "nodelist": ["i-09b9c39571c635328,i-008f0e304d40ca3a2,i-028d109545c7334f8,i-06e26186f161a497a,i-0d44943116b931622,i-0742dc17f9707ecd4,i-0a3cb311d11f5b22a,i-0092e145bacacbb50,i-01ae08da1fefbbc5a,i-0544124d44f45121f,i-0477541c56fbf8333,i-00a6e26c9695fe255,i-06d868abf3f33f852,i-08751f901b3d8cd91,i-02d69237f31355786,i-09425b966ee3c9530,i-09da2dea953dd1bed,i-06ed29b5f2be73029,i-029e274e9c87e92ee,i-0012875cd3aabf5c6,i-020ce554596630f85,i-0a1047f24d3f30c9f,i-0889c960423636da3,i-0a458abb18af676e8,i-09a42753c5b24aa78,i-0997f355da1326bc1,i-024f98dea1d5390a1,i-022ead1bb3f3cfd88,i-08d11416273066ef9,i-02fda578dbaeb41c5,i-0a2a4357b398e5531,i-01d328f0112b6bca5,i-04d7fa1b8f3897468"]}}
```
