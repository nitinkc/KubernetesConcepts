A DaemonSet is a Kubernetes object that ensures **a copy of a specific Pod** runs on every node (or a selected subset of 
nodes) in your cluster.

Unlike a Deployment, which runs a set number of pods spread randomly across available worker nodes (e.g., `replicas: 3`), 
a DaemonSet binds itself to the node lifecycle:

- The DaemonSet is the Kubernetes controller (the rulebook).
- It automatically creates and places a Pod onto every Node in your cluster.

## DaemonSet use cases
**Log Collection & Forwarding Agents:**

Running tools like Fluentd, Logstash, or Datadog Agent so that every node can harvest logs from other containers running on that same node and ship them to a central database.

**Cluster Monitoring & Metrics:**

Running tools like Prometheus Node Exporter to collect CPU, memory, and hardware health metrics from every host.

**Storage Daemons:**

Running distributed storage client daemons (like Ceph or GlusterFS) on every node so pods can mount cluster storage locally.

**Networking & Security Plugins:**

Network proxies (like kube-proxy) or security/compliance scanners that need to inspect or route traffic passing through each specific node.


```shell
kubectl apply -f daemonset-node-info.yml
kubectl get pods -o wide --selector=app=node-info
kubectl port-forward daemonset/node-info-daemonset 8080:80
kubectl delete -f daemonset-node-info.yml

```

```shell
curl http://localhost:8080/
```