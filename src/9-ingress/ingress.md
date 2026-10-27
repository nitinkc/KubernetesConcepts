## Ingress: Path-Based Routing

An Ingress is not a service type; it is a smart Layer 7 traffic controller (reverse proxy) that sits at the very edge 
of your cluster. It listens on standard web ports (`80` for HTTP, `443` for HTTPS) and routes incoming requests based on 
the **URL path or Domain name**.

#### Step 1: Enable the Minikube Ingress Addon
```shell
minikube addons enable ingress
```

#### Step 2: Map my-app.local to your Minikube IP

1. Find your Minikube IP address:
```shell
minikube ip
```

2. Open your computer's hosts file with administrator/sudo privileges:
- Mac / Linux: `/etc/hosts`
- Windows: `C:\Windows\System32\drivers\etc\hosts`

3. Add a new line at the bottom containing your Minikube IP and your custom domain:
```text
192.168.49.2  my-app.local
```

#### Step 3: Keep Minikube Tunnel Active (If Required)
```shell
minikube tunnel
```