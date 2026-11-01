## Ingress: Path-Based Routing

An Ingress is not a service type; it is a smart Layer 7 traffic controller (reverse proxy) that sits at the very edge 
of your cluster. It listens on standard web ports (`80` for HTTP, `443` for HTTPS) and routes incoming requests based on 
the **URL path or Domain name**.

#### Step 1: Enable the Minikube Ingress Addon
```shell
minikube addons enable ingress
```

#### Step 2: Map my-app.local to your Minikube IP

Open your computer's hosts file with administrator/sudo privileges:

- Mac / Linux: `/etc/hosts`
- Windows: `C:\Windows\System32\drivers\etc\hosts`

`minikube tunnel` routes traffic through your local machine (`127.0.0.1`)

3. Add a new line at the bottom containing your Minikube IP and your custom domain:
```text
127.0.0.1  my-app.local
```

#### Step 3: Keep Minikube Tunnel Active (If Required)
```shell
minikube tunnel
```

#### Test

```shell
curl -H "Host: my-app.local" http://127.0.0.1/
```