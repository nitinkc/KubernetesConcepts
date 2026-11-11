"""Regenerate all docs diagrams with real k8s / GCP / network icon shapes.

Replaces the old hand-drawn .drawio.svg files. Icons come from the official
mingrammer `diagrams` packs: k8s.*, gcp.*, onprem.*, generic.*.

Run from repo root:
    uv run --with diagrams python diagrams/generate.py

Output: docs/diagrams/*.png  (dpi=180, docs reference these files)

Design rules — minimal text: icon + 1-3 word label, CIDR/port on second line,
colored cluster boxes for every trust boundary (VPC, subnet, namespace, pod).
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.generic.network import Firewall, Router, Subnet, Switch
from diagrams.generic.compute import Rack
from diagrams.k8s.compute import Deploy, Pod, STS, DS, Job
from diagrams.k8s.network import SVC, Ing, Netpol
from diagrams.k8s.infra import Node, Master
from diagrams.k8s.group import NS
from diagrams.k8s.ecosystem import Helm
from diagrams.onprem.network import Nginx, Envoy, Istio, Internet
from diagrams.onprem.container import Docker
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.logging import FluentBit, Loki
from diagrams.onprem.gitops import Flux
from diagrams.onprem.iac import Terraform
from diagrams.onprem.vcs import Gitlab
from diagrams.onprem.dns import Coredns
from diagrams.onprem.registry import Harbor
from diagrams.onprem.monitoring import Prometheus
from diagrams.onprem.tracing import Jaeger
from diagrams.gcp.network import (VPC, Router as GcpRouter, LoadBalancing, NAT,
                                  FirewallRules, NetworkConnectivityCenter, Routes)
from diagrams.gcp.compute import GKE
from diagrams.gcp.database import SQL
from diagrams.gcp.devtools import ContainerRegistry
from diagrams.gcp.operations import Logging as GcpLogging
from diagrams.gcp.security import Iam

OUT = "docs/diagrams"

GRAPH = dict(dpi="120", bgcolor="white", fontname="Helvetica",
             pad="0.2", nodesep="0.4", ranksep="0.55", splines="spline")
NODE = dict(fontname="Helvetica", fontsize="10",
            imagescale="true", width="0.65", height="0.65")
EDGE_ = dict(fontname="Helvetica", fontsize="9", color="#5f6368", fontcolor="#3c4043")

# Boundary palette (Google palette tints, deepened for legibility)
BLUE = "#d2e3fc"    # node subnet / VPC
GREEN = "#ceead6"   # inside the cluster
YELLOW = "#feefc3"  # ops / bastion
RED = "#fad2cf"     # denied / data tier
PURPLE = "#e9d2fd"  # security / mesh
GRAY = "#e8eaed"    # neutral
TEAL = "#a8dab5"    # observability


def box(color=GRAY, **kw):
    return dict(style="filled", bgcolor=color, color="#80868b",
                fontname="Helvetica-Bold", fontsize="11",
                labeljust="l", margin="12", **kw)


def diag(name, fname, direction="TB", dpi=None):
    g = dict(GRAPH) if dpi is None else {**GRAPH, "dpi": str(dpi)}
    return Diagram(name, filename=f"{OUT}/{fname}", outformat="png",
                   show=False, direction=direction,
                   graph_attr=g, node_attr=NODE, edge_attr=EDGE_)


# ─────────────────────────────────────────────────────────────────────────────
def index_7_layer_stack():
    with diag("The 7-Layer Platform Stack", "index-7-layer-stack", "TB"):
        with Cluster("L7  Mesh & Identity", graph_attr=box(PURPLE)):
            l7 = [Istio("Istio AuthZ"), Envoy("mTLS")]
        with Cluster("L6  GitOps & App Config", graph_attr=box(BLUE)):
            l6 = [Flux("Flux"), Helm("Helm")]
        with Cluster("L5  Observability", graph_attr=box(TEAL)):
            l5 = [FluentBit("logs"), Prometheus("metrics"), Jaeger("traces")]
        with Cluster("L4  Policy & Firewall", graph_attr=box(RED)):
            l4 = [Netpol("NetPol"), Firewall("iptables")]
        with Cluster("L3  Egress & Routing", graph_attr=box(YELLOW)):
            l3 = [Router("routes"), NAT("SNAT")]
        with Cluster("L2  CNI & Overlay", graph_attr=box(GREEN)):
            l2 = [DS("Cilium"), Switch("VXLAN")]
        with Cluster("L1  Underlay / VPC", graph_attr=box(GRAY)):
            l1 = [Subnet("10.10.0.0/24"), Docker("nodes")]
        # invisible chain keeps L7 on top, L1 at the bottom of the stack
        for upper, lower in ((l7, l6), (l6, l5), (l5, l4), (l4, l3), (l3, l2), (l2, l1)):
            upper[0] >> Edge(style="invis") >> lower[0]


# ─────────────────────────────────────────────────────────────────────────────
def index_target_topology():
    with diag("Local Lab ⇄ GCP GKE Twin", "index-target-topology", "LR"):
        with Cluster("Docker host — Minikube 'acme'", graph_attr=box(BLUE)):
            with Cluster("acme-main 10.10.0.0/24", graph_attr=box(GRAY)):
                cp = Master("acme (cp) .10")
                w1 = Node("acme-m02 .11")
                w2 = Node("acme-m03 .12")
                reg = Docker("registry .200")
                with Cluster("dom-* isolated", graph_attr=box(GREEN)):
                    doms = Deploy("orders/payments/inventory")
                cp - [w1, w2, doms]
            with Cluster("acme-ops 10.10.1.0/28", graph_attr=box(YELLOW)):
                pr = Rack("probe .3")
            rtr = Firewall("vpc-router\n.250 / .2")
        pr >> rtr >> [cp, reg]

        with Cluster("GCP — acme VPC", graph_attr=box("#e8f0fe")):
            gcp_vpc = VPC("acme-main")
            gke = GKE("gke-main")
            sql = SQL("commerce-sql\n100.64/20")
            ar = ContainerRegistry("Artifact Registry")
            gr = GcpRouter("Cloud Router\n+ firewall")
            gke - [sql]
        rtr >> Edge(style="dashed", label="1:1 twins") >> gr
        reg >> Edge(style="dashed") >> ar
        gke >> gcp_vpc


# ─────────────────────────────────────────────────────────────────────────────
def lab01_underlay():
    with diag("Lab 01 — Underlay: two subnets, one router, stateful firewall",
              "lab01-underlay-topology", "LR"):
        with Cluster("acme-ops · 10.10.1.0/28", graph_attr=box(YELLOW)):
            probe = Rack("probe .3")
        with Cluster("acme-main · 10.10.0.0/24", graph_attr=box(BLUE)):
            reg = Harbor("registry .200:5000")
            echo = Nginx("echo .201")
        vr = Firewall("vpc-router\nFORWARD DROP\n+ conntrack")
        probe >> Edge(label="1 fwd route") >> vr
        vr >> Edge(label="2 fwd") >> echo
        echo >> Edge(label="3 return route", color="#188038") >> vr
        vr >> Edge(color="#188038") >> probe
        vr - Edge(style="invis") - reg


# ─────────────────────────────────────────────────────────────────────────────
def lab02_address_spaces():
    with diag("Lab 02 — Node / Pod / Service address spaces", "lab02-address-spaces"):
        with Cluster("acme-main 10.10.0.0/24 — node subnet", graph_attr=box(BLUE)):
            with Cluster("pod CIDR 10.20.0.0/20 → /24 per node", graph_attr=box(GREEN)):
                cp = Node("acme .10\n10.20.0.0/24")
                m2 = Node("acme-m02 .11\n10.20.1.0/24")
                m3 = Node("acme-m03 .12\n10.20.2.0/24")
            with Cluster("service CIDR 10.30.0.0/24", graph_attr=box(PURPLE)):
                ks = SVC("kubernetes .1")
                dns = Coredns("kube-dns .10")
        m2 >> Edge(style="dashed", label="VXLAN") >> m3
        cp - [ks, dns]


# ─────────────────────────────────────────────────────────────────────────────
def lab04_four_doors():
    with diag("Lab 04 — default route deleted: four approved egress doors",
              "lab04-four-egress-doors", "LR", dpi=95):
        pod = Pod("pod on m02\n10.20.1.x")
        m3 = Node("m03\ntagged")
        net = Internet("internet")
        pod >> Edge(label="D1 registry", color="#188038") >> Harbor("10.10.0.200:5000")
        pod >> Edge(label="D2 /32", color="#188038") >> net
        pod >> Edge(label="D3 via m03", color="#188038") >> m3
        m3 >> Edge(label="0.0.0.0/0") >> net
        pod >> Edge(label="D4 ops", color="#188038") >> Firewall("vpc-router")
        pod >> Edge(label="else ✗", color="#d93025", style="bold") >> net


# ─────────────────────────────────────────────────────────────────────────────
def lab05_callgraph():
    with diag("Lab 05 — default-deny everywhere; only these paths open",
              "lab05-networkpolicy-callgraph", "LR"):
        with Cluster("dom-orders", graph_attr=box(GRAY)):
            o = Deploy("orders")
        with Cluster("dom-payments", graph_attr=box(GRAY)):
            p = Deploy("payments")
        with Cluster("dom-inventory", graph_attr=box(GRAY)):
            i = Deploy("inventory")
        with Cluster("dom-data", graph_attr=box(RED)):
            cdb = PostgreSQL("commerce-db :5432")
            pdb = PostgreSQL("payments-db :5432")
        dns = Coredns(":53")
        o >> Edge(color="#188038", label=":8080") >> p
        o >> Edge(color="#188038", label=":8080") >> i
        o >> Edge(color="#188038") >> cdb
        i >> Edge(color="#188038") >> cdb
        p >> Edge(color="#188038") >> pdb
        p >> Edge(color="#d93025", label="DENY") >> i
        o >> Edge(color="#d93025", style="dashed", label="DENY") >> pdb
        o - Edge(style="dotted") - dns


# ─────────────────────────────────────────────────────────────────────────────
def lab06_mesh_guards():
    with diag("Lab 06 — two guards, two failure signatures", "lab06-mesh-guards", "LR"):
        with Cluster("pod: caller", graph_attr=box(GRAY)):
            app = Pod("app"); ev1 = Envoy("envoy")
        with Cluster("pod: payments", graph_attr=box(GRAY)):
            ev2 = Envoy("envoy"); srv = Pod("app")
        authz = Netpol("AuthZ\nSPIFFE id")
        plain = Internet("plaintext\ncaller")
        ev1 >> Edge(color="#188038", label="G2 STRICT mTLS → 200") >> ev2
        plain >> Edge(color="#d93025", label="reset") >> ev2
        ev2 >> authz >> srv
        authz - Edge(style="dashed", label="G3 → 403 if not allowed", color="#d93025") - srv


# ─────────────────────────────────────────────────────────────────────────────
def lab07_pod_telemetry():
    with diag("Lab 07 — one pod, four containers, three telemetry paths",
              "lab07-pod-telemetry", "LR"):
        with Cluster("pod 4/4", graph_attr=box(GRAY)):
            app = Pod("app")
            ev = Envoy("envoy")
            fb = FluentBit("fluent-bit\nfile tail")
            ot = Pod("otel\nloopback :4318")
        agent = DS("node agent\nstdout logs")
        with Cluster("observability", graph_attr=box(TEAL)):
            agg = Loki("log-aggregator")
        app >> Edge(label="A stdout") >> agent >> agg
        app >> Edge(label="B emptyDir") >> fb >> agg
        app >> Edge(label="C OTLP") >> ot >> agg
        ev >> Edge(style="dotted", label="stdout") >> agent


# ─────────────────────────────────────────────────────────────────────────────
def lab08_gauntlet():
    with diag("Lab 08 — North-South gauntlet: four guards", "lab08-ingress-gauntlet", "LR"):
        pr = Rack("probe 10.10.1.3")
        g1 = Firewall("G1 vpc-router\nFORWARD :80?")
        g2 = SVC("G2 MetalLB VIP\n10.10.0.240-249")
        g3 = Envoy("G3 STRICT mTLS")
        g4 = Netpol("G4 AuthZ /\nNetPol")
        pods = Pod("orders pods")
        pr >> g1 >> g2 >> g3 >> g4 >> pods


# ─────────────────────────────────────────────────────────────────────────────
def lab09_flux_tiers():
    with diag("Lab 09 — Flux dependency tiers: order keeps rebuilds green",
              "lab09-flux-tiers", "LR"):
        repo = Gitlab("flux-releases-local\nclusters/local")
        fx = Flux("flux")
        with Cluster("10 controllers", graph_attr=box(GRAY)):
            t1 = [DS("cilium"), Istio("istiod"), SVC("metallb")]
        with Cluster("20 configs", graph_attr=box(GRAY)):
            t2 = [NS("labeled ns"), Netpol("netpols"), Netpol("STRICT/AuthZ"), Loki("log-agg")]
        with Cluster("25 data", graph_attr=box(RED)):
            t3 = [STS("commerce-db"), STS("payments-db"), Job("seed")]
        with Cluster("30 apps", graph_attr=box(GREEN)):
            t4 = [Deploy("orders"), Deploy("payments"), Deploy("inventory")]
        repo >> fx
        fx >> Edge(label="dependsOn 1") >> t1[0]
        t1[0] >> Edge(label="2") >> t2[0]
        t2[0] >> Edge(label="3") >> t3[0]
        t3[0] >> Edge(label="4") >> t4[0]


# ─────────────────────────────────────────────────────────────────────────────
def adr_ipam():
    with diag("Master IPAM blueprint — allocate all classes before building",
              "adr-ipam-blueprint"):
        with Cluster("node layer — routable", graph_attr=box(BLUE)):
            Subnet("nodes 10.10.0.0/24"); Rack("ops 10.10.1.0/28")
        with Cluster("cluster layer — inside", graph_attr=box(GREEN)):
            Pod("pods 10.20.0.0/20\n→ /24 per node")
            SVC("svc 10.30.0.0/24")
        with Cluster("GCP managed — non-transitive", graph_attr=box(PURPLE)):
            Master("gke-master 10.10.250.0/28")
            LoadBalancing("proxy-only 10.10.254.0/23")
            SQL("PSA 100.64.0.0/20")


# ─────────────────────────────────────────────────────────────────────────────
def adr_isolation():
    with diag("ADR-01 — one cluster vs three clusters", "adr-cluster-isolation", "LR"):
        with Cluster("Option A — 1 cluster + layered zero-trust  ✓ chosen",
                     graph_attr=box(GREEN)):
            g1 = GKE("cluster")
            with Cluster("namespaces", graph_attr=box(GRAY)):
                a = [NS("dom-orders"), NS("dom-payments"), NS("dom-inventory")]
            g1 - a
            shields = [Netpol("L4"), Envoy("L7"), Iam("WI")]
            g1 - shields
        with Cluster("Option B — 3 clusters (compliance / cadence / region)",
                     graph_attr=box(YELLOW)):
            b = [GKE("gke-orders"), GKE("gke-payments"), GKE("gke-inventory")]


# ─────────────────────────────────────────────────────────────────────────────
def adr_telemetry():
    with diag("ADR-04 — three telemetry patterns", "adr-telemetry-patterns", "LR"):
        with Cluster("A — stdout → node agent", graph_attr=box(GRAY)):
            a1 = Pod("app stdout"); a2 = DS("node agent")
            a1 >> a2
        with Cluster("B — emptyDir → fluent-bit", graph_attr=box(GRAY)):
            b1 = Pod("app file"); b2 = FluentBit("tail :24224")
            b1 >> b2
        with Cluster("C — loopback OTLP", graph_attr=box(GRAY)):
            c1 = Pod("app :4318"); c2 = Pod("otel")
            c1 >> c2
        sink = Loki("backend")
        a2 >> sink; b2 >> sink; c2 >> sink


# ─────────────────────────────────────────────────────────────────────────────
def adr_tf_flux():
    with diag("ADR-05 — Terraform owns the cloud, Flux owns the cluster",
              "adr-terraform-flux-handshake", "LR"):
        tf = Terraform("Terraform")
        with Cluster("cloud objects", graph_attr=box(BLUE)):
            c1 = VPC("VPC/routes"); c2 = GKE("GKE+pools"); c3 = Iam("GSA+WI")
        fx = Flux("Flux")
        with Cluster("in-cluster objects", graph_attr=box(GREEN)):
            f1 = DS("10 controllers"); f2 = Netpol("20 configs"); f3 = Deploy("30 apps")
        tf >> Edge(label="writes") >> [c1, c2, c3]
        fx >> Edge(label="reconciles") >> [f1, f2, f3]
        c2 >> Edge(style="dashed", label="hands off context") >> fx


# ─────────────────────────────────────────────────────────────────────────────
def rosetta():
    with diag("Local Lab ⇄ GCP — same architecture, managed twin objects",
              "rosetta-local-vs-gcp", "LR"):
        with Cluster("local (docker + minikube)", graph_attr=box(GRAY)):
            l1 = Docker("bridge nets"); l2 = Router("vpc-router"); l3 = Firewall("iptables FORWARD")
            l4 = Node("minikube"); l5 = Harbor("registry"); l6 = SVC("MetalLB"); l7 = Flux("Flux")
        with Cluster("GCP", graph_attr=box(BLUE)):
            r1 = VPC("VPC"); r2 = GcpRouter("routes"); r3 = FirewallRules("VPC firewall")
            r4 = GKE("GKE DPV2"); r5 = ContainerRegistry("Artifact Reg"); r6 = LoadBalancing("gke-l7-rilb"); r7 = Gitlab("Config Sync")
        l1 >> Edge(style="dashed") >> r1; l2 >> Edge(style="dashed") >> r2
        l3 >> Edge(style="dashed") >> r3; l4 >> Edge(style="dashed") >> r4
        l5 >> Edge(style="dashed") >> r5; l6 >> Edge(style="dashed") >> r6
        l7 >> Edge(style="dashed") >> r7


# ─────────────────────────────────────────────────────────────────────────────
def lab11_topology():
    with diag("Lab 11 — hub-and-spoke federation (NCC + MCS twins)",
              "lab11-topology", "LR"):
        with Cluster("acme-ops 10.10.1.0/28", graph_attr=box(YELLOW)):
            pr = Rack("probe .3")
        hub = NetworkConnectivityCenter("vpc-router hub\n.250 legs")
        with Cluster("us — acme-main 10.10.0.0/24", graph_attr=box(BLUE)):
            us = GKE("acme-us id:1\npods 10.20/20")
        with Cluster("eu — acme-eu 10.11.0.0/24", graph_attr=box(GREEN)):
            eu = GKE("acme-eu id:2\npods 10.21/20")
        with Cluster("asia — acme-asia 10.12.0.0/24", graph_attr=box(PURPLE)):
            ap = GKE("acme-asia id:3\npods 10.22/20")
        for c in (us, eu, ap):
            c >> Edge(style="bold") >> hub
        pr >> Edge(style="dashed", label="authorized nets only") >> hub
        us >> Edge(style="dotted", label="ClusterMesh sync", color="#188038") >> eu


if __name__ == "__main__":
    import pathlib
    pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    for f in (index_7_layer_stack, index_target_topology, lab01_underlay,
              lab02_address_spaces, lab04_four_doors, lab05_callgraph,
              lab06_mesh_guards, lab07_pod_telemetry, lab08_gauntlet,
              lab09_flux_tiers, adr_ipam, adr_isolation, adr_telemetry,
              adr_tf_flux, rosetta, lab11_topology):
        f()
        print("ok:", f.__name__)
    print("done →", OUT)
