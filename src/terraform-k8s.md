When deciding whether to manage Kubernetes objects (like RBAC, ServiceAccounts, Deployments, and Services) via Terraform
or native Kubernetes manifests, the industry follows a core golden rule:

Use Terraform for Infrastructure, and Kubernetes (or GitOps) for Workloads and Cluster Configuration.

While Terraform can manage almost any Kubernetes object using the Kubernetes provider, doing everything through 
Terraform quickly becomes an operational bottleneck.




