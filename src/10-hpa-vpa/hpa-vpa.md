HPA vs. VPA: The Key DifferencePeople often confuse VPA with HPA because both are autoscalers, but they solve completely 
different problems:  

**HPA (Horizontal Pod Autoscaler)**: Changes the number of pods. If traffic spikes, it scales from 3 replicas to 10 replicas. 
(Scaling out)

**VPA (Vertical Pod Autoscaler)**: Changes the size of the pods. Instead of adding more pods, it gives an existing 
pod more (or less) CPU and memory. (Scaling up or down)   

A VPA system relies on three core internal components working together:

**The Recommender:** 
It continuously tracks historical resource usage (CPU and memory trends, peak usage, and OOM events).
It outputs a recommendation: a `Target` size, a `Lower Bound`, and an `Upper Bound`.

**The Admission Controller (Webhook):**
Whenever a brand-new pod is created (or recreated), this component intercepts the request and injects the
VPA's optimized resource values right into the pod spec.

**The Updater:** 
It watches running pods. If a running pod's resource usage drifts too far from the recommendation, 
the Updater can apply the new size based on your chosen configuration.
