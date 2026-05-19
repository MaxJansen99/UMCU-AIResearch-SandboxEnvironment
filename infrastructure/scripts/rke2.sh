#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

dnf install -y kernel-modules-extra

firewall-cmd --permanent --add-port=6443/tcp
firewall-cmd --permanent --add-port=9345/tcp
firewall-cmd --permanent --add-port=10250/tcp
firewall-cmd --permanent --add-port=2379/tcp
firewall-cmd --permanent --add-port=2380/tcp
firewall-cmd --permanent --add-port=2381/tcp
firewall-cmd --permanent --add-port=30000-32767/tcp
firewall-cmd --permanent --add-port=8472/udp
firewall-cmd --permanent --add-port=9099/tcp
firewall-cmd --permanent --add-port=51820/udp
firewall-cmd --permanent --add-port=51821/udp
firewall-cmd --reload

mkdir -p /etc/NetworkManager/conf.d

tee /etc/NetworkManager/conf.d/rke2-canal.conf >/dev/null <<'EOF'
[keyfile]
unmanaged-devices=interface-name:flannel*;interface-name:cali*;interface-name:tunl*;interface-name:vxlan.calico;interface-name:vxlan-v6.calico;interface-name:wireguard.cali;interface-name:wg-v6.cali
EOF

systemctl reload NetworkManager

mkdir -p /etc/rancher/rke2/

read -rp "RKE2_DOMAIN_NAME=" RKE2_DOMAIN_NAME

tee /etc/rancher/rke2/config.yaml >/dev/null <<EOF
write-kubeconfig-mode: "0644"
tls-san:
  - "${RKE2_DOMAIN_NAME}"
node-label:
  - "role=single-node"
debug: true
EOF

export RKE2_MINOR=33
export LINUX_MAJOR=10
cat <<EOF >/etc/yum.repos.d/rancher-rke2-1-${RKE2_MINOR}-latest.repo
[rancher-rke2-common-latest]
name=Rancher RKE2 Common Latest
baseurl=https://rpm.rancher.io/rke2/latest/common/centos/${LINUX_MAJOR}/noarch
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://rpm.rancher.io/public.key

[rancher-rke2-1-${RKE2_MINOR}-latest]
name=Rancher RKE2 1.${RKE2_MINOR} Latest
baseurl=https://rpm.rancher.io/rke2/latest/1.${RKE2_MINOR}/centos/${LINUX_MAJOR}/x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://rpm.rancher.io/public.key
EOF

dnf -y install rke2-server

systemctl enable --now rke2-server.service

# STEP 1: Docker Registry
echo "Exchange 1: RKE2 <- GitLab: Docker Registry"

read -rp "GITLAB_DOMAIN_NAME=" GITLAB_DOMAIN_NAME

echo "Paste .crt content, then press Ctrl-D:"
tee "/etc/rancher/rke2/${GITLAB_DOMAIN_NAME}.crt" >/dev/null

# STEP 1.2:
echo "Group -> Settings -> Repository -> Deploy Tokens"
echo "Create deploy token on GitLab and paste content"

read -rp "DEPLOY_NAME=" DEPLOY_NAME
read -rp "DEPLOY_TOKEN=" DEPLOY_TOKEN

tee /etc/rancher/rke2/registries.yaml >/dev/null <<EOF
mirrors:
  "${GITLAB_DOMAIN_NAME}:5050":
    endpoint:
      - "https://${GITLAB_DOMAIN_NAME}:5050"
configs:
  "${GITLAB_DOMAIN_NAME}:5050":
    auth:
      username: ${DEPLOY_NAME}
      password: ${DEPLOY_TOKEN}
    tls:
      ca_file: "/etc/rancher/rke2/${GITLAB_DOMAIN_NAME}.crt"
EOF

systemctl restart rke2-server.service

exit 0
#------------------------------------------------------------

# echo "Exchange 2: RKE2 -> GitLab: Kube Config"

# STEP 2: Kubernetes
# UTILITIES (kubectl, crictl and ctr)
# export PATH=$PATH://var/lib/rancher/rke2/bin/

mkdir -p ~/.kube/
cp /etc/rancher/rke2/rke2.yaml ~/.kube/config

echo "Copy contents of .kube/config and change address to ${RKE2_DOMAIN_NAME}"
cat ~/.kube/config
read -rp "Press Enter to continue..."
