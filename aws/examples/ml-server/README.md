# Machine Learning Server

For this experiment we will demonstrate a prototype that uses HPC alongside usernetes, specifically training and testing a model.
We will be using [lammps-stream-ml](https://github.com/converged-computing/lammps-stream-ml). To start:

```
cd ~/usernetes
```
Note that we need to update the docker-compose.yaml to include port 8080. You can do that manually, or just:

```console
wget -O docker-compose-ml.yaml https://gist.githubusercontent.com/vsoch/69034d0bf8f4d009935aa2a0f84072c6/raw/077731396bebb0944305ec36fb8c9e8bbf1d171a/docker-compose.yaml
flux archive create --name=docker-compose --mmap -C /home/ubuntu/usernetes docker-compose-ml.yaml
flux exec -x 0 -r all flux archive extract --name=docker-compose -C /home/ubuntu/usernetes
flux exec -r all --dir /home/ubuntu/usernetes mv docker-compose-ml.yaml docker-compose.yaml
```

After that, you should see this in ports of the main `docker-compose.yaml`

```yaml
    ports:
      # ml-server
      - 8080:8080
```

And then start usernetes:

```bash
./start-control-plane.sh
```

And then send over the join command, and do a replace.

```bash
flux archive create --name=join-command --mmap -C /home/ubuntu/usernetes join-command
flux exec -x 0 -r all flux archive extract --name=join-command -C /home/ubuntu/usernetes
flux exec -x 0 -r all --dir /home/ubuntu/usernetes /bin/bash ./start-worker.sh
```

Ensure you have your nodes.

```bash
. ~/.bashrc
kubectl get nodes
```

## 1. Build Containers

This first required [building containers for arm](https://github.com/converged-computing/lammps-stream-ml/blob/main/docs/containers.md).
I cloned the repository, did the build, and pushed to a registry.

```
mkdir -p /home/ubuntu/ml-server
cd /home/ubuntu/ml-server
git clone https://github.com/converged-computing/flux-usernetes
cd flux-usernetes/aws/examples/ml-server
```

Ensure we tweak the flags for arm.

```bash
docker build -f Dockerfile.arm -t ghcr.io/converged-computing/lammps-stream-ml:server-arm .
docker build -f Dockerfile.client-arm -t ghcr.io/converged-computing/lammps-stream-ml:client-arm .
```

For our lammps image, we are using the same one (from the lammps experiment) here, but adding lammps to it.

```bash
cd ./docker
docker build -t ghcr.io/converged-computing/lammps-stream-ml:lammps-arm .
```

And ensure you push all of them to a registry.

```console
docker push ghcr.io/converged-computing/lammps-stream-ml:server-arm
docker push ghcr.io/converged-computing/lammps-stream-ml:client-arm
docker push ghcr.io/converged-computing/lammps-stream-ml:lammps-arm
```

## 2. Kubernetes

You should already have usernetes running on your setup.

```bash
# Autocomplete
source <(kubectl completion bash) 
```

### Ingress

We then want to create a service to access the TBA ml-service.

```bash
kubectl apply -f crd/ingress.yaml
```
```console
$ kubectl describe ingress
Name:             ml-ingress
Labels:           <none>
Namespace:        default
Address:          
Ingress Class:    <none>
Default backend:  <default>
Rules:
  Host        Path  Backends
  ----        ----  --------
  localhost   
              /   ml-service:8080 (<none>)
Annotations:  <none>
Events:       <none>
```

We are then going to apply [ingress-nginx](https://kind.sigs.k8s.io/docs/user/ingress/#ingress-nginx),
but install with helm so we get the arm variant.

```console
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx --namespace kube-system
```

### Deployment

Deploy the machine learning server.

```bash
kubectl apply -f crd/server-deployment.yaml
```

Note that we have hard coded secrets, which is OK for local testing, but you should update these to a secret proper for anything more than that. If the ingress and deployment are successful, you should have the server deployed to a node. Here is how to get the node:

```bash
kubectl  get pods -o wide
```
```console
NAME                         READY   STATUS    RESTARTS   AGE     IP           NODE                      NOMINATED NODE   READINESS GATES
ml-server-6547db94fd-qjwkb   1/1     Running   0          6m32s   10.244.1.5   u7s-i-0ba186b66890a2230   <none>           <none>
```

In the above, we can find it deployed to u7s-i-0ba186b66890a2230 which is _not_ our control plane we are sitting on (localhost).

```bash
curl -k i-0c79705f628c562a3:8080/api/
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

Since we want to run lammps, let's test writing a container and script to do that next. Our current container has the client for river, but not lammps. Let's combine the two.

### Create Models

Let's create three empty models. Since we know the service is running, we can now
pull the same lammps container that we will use for the jobs (and run a script to create models, which is prepared inside).
We will need this container anyway to run lammps, might as well use it for other things!

```bash
flux exec -r all mkdir -p /home/ubuntu/ml-server
flux exec -r all --dir /home/ubuntu/ml-server singularity pull docker://ghcr.io/converged-computing/lammps-stream-ml:lammps-arm
```

Here is how to create the models for the running server. The names will be funny but largely don't matter - we can get them programmatically later.

```bash
# We need to run this from the lammps root
cd /home/ubuntu/lammps

# Set the container path
container=/home/ubuntu/ml-server/lammps-stream-ml_lammps-arm.sif

# Install the riverapi for local interaction
python3 -m pip install riverapi 

# Set your host
host=http://i-0c79705f628c562a3:8080

# Assumes service running on localhost directory (first parameter, default)
singularity exec $container python3 /code/1-create-models.py $host
```
```console
Preparing to create models for client URL http://localhost
Created model expressive-cupcake
Created model confused-underoos
Created model doopy-platanos
```

### Train lammps

Copy the script into the lammps directory, for easy access.

```bash
cp /home/ubuntu/ml-server/flux-usernetes/aws/examples/ml-server/docker/scripts/2-run-lammps-flux.py .
```

We can now run jobs with flux (train):

```
python3 2-run-lammps-flux.py train --container $container --np 32 --nodes 2 --workdir /opt/lammps/examples/reaxff/HNS --x-min 1 --x-max 32 --y-min 1 --y-max 8 --z-min 1 --z-max 16 --iters 1 --in --url $host
```

That is a test run - adjust `--ters` to be a larger number for actual training! And the job size to match your resources.

### Predict LAMMPS

Now let's generate more data, but this time, compare the actual time with each model prediction. This script is very similar but calls a different API function.

```bash
python3 2-run-lammps-flux.py predict --container $container --np 32 --nodes 2 --workdir /opt/lammps/examples/reaxff/HNS --x-min 1 --x-max 32 --y-min 1 --y-max 8 --z-min 1 --z-max 16 --iters 3 --url $host --out test-predict.json
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
⭐️ Performance for: confused-underoos
          R Squared Error: -0.3754428092605011
       Mean Squared Error: 211.76317491374675
      Mean Absolute Error: 12.15553921176494
  Root Mean Squared Error: 14.55208489920763

⭐️ Performance for: doopy-platanos
          R Squared Error: -2.1591108103954655
       Mean Squared Error: 486.3767003684858
      Mean Absolute Error: 19.646310895303525
  Root Mean Squared Error: 22.05394976797775

⭐️ Performance for: expressive-cupcake
          R Squared Error: -0.06854277833132616
       Mean Squared Error: 164.5128461518909
      Mean Absolute Error: 11.27571565875684
  Root Mean Squared Error: 12.826256123744407
```

Negative R squared, lol. 😬️

