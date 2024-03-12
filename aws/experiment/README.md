# Flux Usernetes Experiment on AWS

### Lammps and OSU Benchmarks

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
And some extra flux info:

```
$ flux resource info
33 Nodes, 528 Cores, 0 GPUs
ubuntu@i-09b9c39571c635328:~$ flux resource R
{"version": 1, "execution": {"R_lite": [{"rank": "0-32", "children": {"core": "0-15"}}], "starttime": 0.0, "expiration": 0.0, "nodelist": ["i-09b9c39571c635328,i-008f0e304d40ca3a2,i-028d109545c7334f8,i-06e26186f161a497a,i-0d44943116b931622,i-0742dc17f9707ecd4,i-0a3cb311d11f5b22a,i-0092e145bacacbb50,i-01ae08da1fefbbc5a,i-0544124d44f45121f,i-0477541c56fbf8333,i-00a6e26c9695fe255,i-06d868abf3f33f852,i-08751f901b3d8cd91,i-02d69237f31355786,i-09425b966ee3c9530,i-09da2dea953dd1bed,i-06ed29b5f2be73029,i-029e274e9c87e92ee,i-0012875cd3aabf5c6,i-020ce554596630f85,i-0a1047f24d3f30c9f,i-0889c960423636da3,i-0a458abb18af676e8,i-09a42753c5b24aa78,i-0997f355da1326bc1,i-024f98dea1d5390a1,i-022ead1bb3f3cfd88,i-08d11416273066ef9,i-02fda578dbaeb41c5,i-0a2a4357b398e5531,i-01d328f0112b6bca5,i-04d7fa1b8f3897468"]}}
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

