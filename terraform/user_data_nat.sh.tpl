#!/bin/bash
set -eux

dnf update -y

sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf

PUBLIC_IFACE=$(ip route show default | awk '/default/ {print $5}' | head -n 1)

iptables -t nat -A POSTROUTING -o $PUBLIC_IFACE -j MASQUERADE
iptables -A FORWARD -i $PUBLIC_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -o $PUBLIC_IFACE -j ACCEPT

dnf install -y iptables-services
service iptables save
systemctl enable iptables