

pod to pod communication

```shell
kubectl port-forward  30080:80
```

## Run all files

```shell
kubectl apply -f .
kubectl delete -f .
```


```shell
 kubectl port-forward svc/frontend-service 30081:80
```