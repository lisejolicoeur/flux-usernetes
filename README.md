# Flux Usernetes on Azure

We don't have Terraform yet, so this is a "GUI" experience at the moment.

## Usage

### 1. Build Images

Since I'm new to Azure, I'm starting by creating a VM and then saving the image, which I did through the console (and saved the template) and all of the associated scripts are in [build-images](build-images). I chose:

- ubuntu server 22.04
- South Central US
- Zone (allow auto select)
- HB120-16rs_v3 (about $4/hour)
- username: azureuser
- select your ssh key
- defaults to 30GB disk, but you should make it bigger - I skipped installing Singularity the first time because I ran out of room.

And interactively I ran each of:

- install-deps.sh
- install-flux.sh
- install-usernetes.sh
- install-singularity.sh (skipped)
- install-lammps.sh 

And then you can actually click to create the instance group in the user interface, and it's quite easy.
You MUST call it `flux-usernetes` to derive the machine names as flux-userxxxxx OR change that prefix in the startup-script.sh
In addition, you will need to:

- Add the `startup-script.sh` to the user data section (ensure the hostname is going to be correct)
- Ensure you click on the network setup and enable the public ip address so you can ssh in
- use a pem key over a password
- Open up ports 22 for ssh, and 8050 for the flux brokers

### 2. Check Flux

Check the cluster status, the overlay status, and try running a job:

```bash
$ flux resource list
```
```bash
$ flux run -N 2 hostname
```

And lammps?

```bash
cd /home/azureuser/lammps
flux run -N 2 --ntasks 96 -c 1 -o cpu-affinity=per-task /usr/bin/lmp -v x 2 -v y 2 -v z 2 -in ./in.reaxff.hns -nocite
```

If you need to check memory that is seen by flux:

```bash
$ flux run sh -c 'ulimit -l' --rlimit=memlock
64
```

### 3. Start Usernetes

Usernetes can be started manually from the head node.
For the controle plane:

```bash
$ cd ~/usernetes
$ ./start-control-plane.sh
```
For the worker nodes:
```bash
$ flux archive create --name=join-command --mmap -C /home/azureuser/usernetes join-command
$ flux exec -x 0 -r all flux archive extract --name=join-command -C /home/azureuser/usernetes
$ cd /home/azureuser/usernetes
$ flux exec -x 0 -r all --dir /home/azureuser/usernetes /bin/bash ./start-worker.sh
```
```bash
$ export KUBECONFIG=/home/azureuser/usernetes/kubeconfig
$ make sync-external-ip
```
Then we can check all the nodes are correctly initialized:
```bash
$ kubectl get nodes -o wide
```
And finally, we can install the Flux Operator (x86 version) :
```bash
$ kubectl apply -f https://raw.githubusercontent.com/flux-framework/flux-operator/main/examples/dist/flux-operator.yaml
```

### 4. Deploying a MiniCluster with Infiniband for OSU benchmarks

This deployment uses a custom Docker image that has Flux, OSU and OpenMPI with a default configuration for the x86 architecture. The Dockerfile used to create this image is in `osu-benchmarks/`.

A manifest for a basic MiniCluster deployment is given in `osu-benchmarks/flux-osu-ib.yaml`. RDMA is made available to the pods by mounting `/dev/` and `/sys/`. It is important to note that there will be no Infiniband IP interface in the Pod (ib0) as we are only mounting the RDMA interface. This is enough for MPI applications that don't rely extensively on TCP/IP communications but if they do it might be interesting to also have the IPoIB interface in the Pod (see add-azure branch section 4).

To deploy this MiniCluster:
```bash
$ kubectl apply -f osu-benchmarks/flux-osu-ib.yaml
```

### 5. Testing the network

To check that we have access to RDMA in the Pod, we can use the `ibv_devinfo` command:
```bash
$ kubectl exec -ti flux-sample-0-XXXXX /bin/bash
$ ibv_devinfo
```
You should be able to see the "mlx5\_ib0" interface. You can also test basic RDMA operations using the `ibv_rc_pingpong` command between two pods. Shell into each Pod on different terminals, on one terminal execute :
```bash
$ ibv_rc_pingpong
```
And in the other terminal execute:
```bash
$ ibv_rc_pingpong <IP of the other Pod eth0 interface>
```

Next, we can test that OpenMPI works correctly with RDMA by running an OSU benchmark.
First connect to the flux broker in the pod:
```bash
$ kubectl exec -ti flux-sample-0-XXXXX /bin/bash
$ flux proxy local:///mnt/flux/view/run/flux/local bash
$ flux resource list
```
Before executing an OSU benchmark, we need to make sure 2 environment variables are set. First we want to set `OMPI_MCA_pml`:
```bash
$ export OMPI_MCA_pml=ucx
```
We're going to use UCX as our networking library here, as opposed to OFI for example (which we used for EFA). Along with this, we'll define the type of transport we want UCX to use as `everything but tcp`. Having tcp will throw an error because `somaxconn` does not exist in the container (I don't know why). At the same time, using `ib` as a transport type yields bad performance as it seems shared memory is not used.
```bash
$ export UCX_TLS=^tcp
```
Important to mention here : if the MiniCluster was created without /dev/shm mounted, it will fail at execution saying /dev/shm is too small. In this case, we want to define the transport as being `ib`. It will work, but the performance will not be as good.

Now we can run any OSU benchmark, for example `osu_latency`:
```bash
$ flux run -N2 -n2 c/mpi/pt2pt/standard/osu_latency
```
