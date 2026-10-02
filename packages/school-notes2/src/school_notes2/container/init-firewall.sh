#!/bin/bash
# Outbound firewall of the agent container (plan 7.3), after the Claude Code devcontainer
# init-firewall.sh pattern: default DROP; allowed are loopback, DNS, replies, and HTTPS to
# the configured provider domains, resolved at every start. Runs as container root with
# NET_ADMIN, which rootless Podman confines to the container's own network namespace.
# Exit codes: 0 ok, 11 a provider domain did not resolve (network, transient),
# 12 a rule could not be loaded.
set -u

domains=${SN_ALLOWED_DOMAINS:-}
if [ -z "$domains" ]; then
    echo "sn-init-firewall: SN_ALLOWED_DOMAINS is empty" >&2
    exit 12
fi

rule() {
    if ! "$@"; then
        echo "sn-init-firewall: failed: $*" >&2
        exit 12
    fi
}

for cmd in iptables ip6tables; do
    rule "$cmd" -F OUTPUT
    rule "$cmd" -A OUTPUT -o lo -j ACCEPT
    rule "$cmd" -A OUTPUT -p udp --dport 53 -j ACCEPT
    rule "$cmd" -A OUTPUT -p tcp --dport 53 -j ACCEPT
    rule "$cmd" -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
done

# Plain per-address rules instead of an ipset: this exact form is what was verified on the VM.
IFS=',' read -r -a list <<< "$domains"
for domain in "${list[@]}"; do
    addrs=$(dig +short +time=3 +tries=2 A "$domain" | grep -E '^[0-9]+(\.[0-9]+){3}$')
    if [ -z "$addrs" ]; then
        echo "sn-init-firewall: cannot resolve $domain" >&2
        exit 11
    fi
    for ip in $addrs; do
        rule iptables -A OUTPUT -d "$ip" -p tcp --dport 443 -j ACCEPT
    done
done

rule iptables -P OUTPUT DROP
rule ip6tables -P OUTPUT DROP
exit 0
