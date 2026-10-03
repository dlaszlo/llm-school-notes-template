#!/bin/bash
# Outbound firewall of the agent container (plan 7.3), after the Claude Code devcontainer
# init-firewall.sh pattern: default DROP; allowed are loopback, DNS to the container's own
# resolvers only, replies, and HTTPS to the configured provider domains, resolved at every
# start. Runs as container root with NET_ADMIN, which rootless Podman confines to the
# container's own network namespace.
# Exit codes: 0 ok, 211 a provider domain did not resolve (network, transient),
# 212 a rule could not be loaded or no resolver is configured.
set -u

domains=${SN_ALLOWED_DOMAINS:-}
if [ -z "$domains" ]; then
    echo "sn-init-firewall: SN_ALLOWED_DOMAINS is empty" >&2
    exit 212
fi

rule() {
    if ! "$@"; then
        echo "sn-init-firewall: failed: $*" >&2
        exit 212
    fi
}

# Port 53 only towards the resolvers of /etc/resolv.conf: an open port 53 to any address
# would be a tunnel to any host.
resolvers=$(awk '$1 == "nameserver" {print $2}' /etc/resolv.conf)
if [ -z "$resolvers" ]; then
    echo "sn-init-firewall: no nameserver in /etc/resolv.conf" >&2
    exit 212
fi

for cmd in iptables ip6tables; do
    rule "$cmd" -F OUTPUT
    rule "$cmd" -A OUTPUT -o lo -j ACCEPT
    rule "$cmd" -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
done
for ns in $resolvers; do
    case "$ns" in
        *:*) cmd=ip6tables ;;
        *)   cmd=iptables ;;
    esac
    rule "$cmd" -A OUTPUT -d "$ns" -p udp --dport 53 -j ACCEPT
    rule "$cmd" -A OUTPUT -d "$ns" -p tcp --dport 53 -j ACCEPT
done

# Plain per-address rules instead of an ipset: this exact form is what was verified on the VM.
IFS=',' read -r -a list <<< "$domains"
for domain in "${list[@]}"; do
    addrs=$(dig +short +time=3 +tries=2 A "$domain" | grep -E '^[0-9]+(\.[0-9]+){3}$')
    if [ -z "$addrs" ]; then
        echo "sn-init-firewall: cannot resolve $domain" >&2
        exit 211
    fi
    for ip in $addrs; do
        rule iptables -A OUTPUT -d "$ip" -p tcp --dport 443 -j ACCEPT
    done
done

rule iptables -P OUTPUT DROP
rule ip6tables -P OUTPUT DROP
exit 0
