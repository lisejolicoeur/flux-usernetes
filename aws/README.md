# Flux Usernetes on AWS

Terraform module to create Amazon Machine Images (AMI) for Flux Framework and AWS CodeBuild.
This used to use packer, but it stopped working so now the build is a bit manual for the AMI.

## Usage

### 1. Build Images

Note that we previously built with packer. That no longer seems to work ([maybe this issue](https://github.com/hashicorp/packer/issues/8180))
Instead we are going to run the commands there manually and save the AMI. The previous instruction was to export AWS credentials, cd into build-images,
and `make`. For the manual build, you'll need to create an m5.large instance in the web UI, ubuntu 22.04, and manually run the contents of each
of the scripts in [build-images](build-images). For example, for the top AMI below I ran each of:

- install-deps.sh
- install-flux.sh
- install-usernetes.sh
- install-singularity.sh
- install-lammps.sh

And this generated:

- flux-ubuntu-usernetes: `ami-023a3bf52034d3faa` has flux, usernetes, lammps, and singularity


### Deploy with Terraform

Once you have images, choose a directory under [examples](examples) to deploy from:

```bash
$ cd tf
```

And then init and build:

```bash
$ make init
$ make fmt
$ make validate
$ make build
```

And they all can be run with `make`:

```bash
$ make
```

You can then shell into any node, and check the status of Flux. I usually grab the instance
name via "Connect" in the portal, but you could likely use the AWS client for this too.

```bash
$ ssh -o 'IdentitiesOnly yes' -i "mykey.pem" ubuntu@ec2-xx-xxx-xx-xxx.compute-1.amazonaws.com
```

#### Check Flux

Check the cluster status, the overlay status, and try running a job:

```bash
$ flux resource list
     STATE NNODES   NCORES NODELIST
      free      2        2 i-012fe4a110e14da1b,i-0354d878a3fd6b017
 allocated      0        0 
      down      0        0 
```
```bash
$ flux run -N 2 hostname
i-012fe4a110e14da1b.ec2.internal
i-0354d878a3fd6b017.ec2.internal
```

You can look at the startup script logs like this if you need to debug.

```bash
$ cat /var/log/cloud-init-output.log
```

That's it. Enjoy!

#### Start Usernetes

This is currently manual, and I haven't found a way to automate it - cloud init cannot run these commands.

##### Control Plane

Here is setup:

```bash
/usr/bin/dockerd-rootless-setuptool.sh uninstall -f 
/usr/bin/rootlesskit rm -rf /home/ubuntu/.local/share/docker
sudo chown -R $USER /home/ubuntu
dockerd-rootless-setuptool.sh install
docker run hello-world

cd ~/usernetes
./start-control-plane.sh
flux filemap map -C /home/ubuntu/usernetes join-command
flux exec -x 0 -r all flux filemap get -C /home/ubuntu/usernetes    
```

##### Worker Nodes

```bash
/usr/bin/dockerd-rootless-setuptool.sh uninstall -f 
/usr/bin/rootlesskit rm -rf /home/ubuntu/.local/share/docker
sudo chown -R $USER /home/ubuntu
dockerd-rootless-setuptool.sh install
docker run hello-world

cd ~/usernetes
./start-worker.sh
```

Check (from the first node) that usernetes is running:

```
kubectl get pods
```
