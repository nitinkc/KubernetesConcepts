
Unlike Daemonset, job & cronjob run on a single node chosen dynamically by the Kubernetes scheduler.

When a Job is triggered, it creates a temporary Pod.

The Kubernetes scheduler looks at your cluster, finds the best available node with enough free CPU and RAM, and places that single pod there.

Once the task finishes successfully, the pod shuts down and does not restart.