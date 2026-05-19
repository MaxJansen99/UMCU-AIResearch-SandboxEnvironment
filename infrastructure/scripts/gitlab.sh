#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

dnf -y install dnf-plugins-core

dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker.service

dnf install -y curl

firewall-cmd --permanent --add-port=22/tcp
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --permanent --add-port=5050/tcp
firewall-cmd --reload

curl --location "https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.rpm.sh" | bash

# NOG NIET HELEMAAL GOED
#------------------------------------------------------------
dnf install -y gitlab-ce

read -rp "GITLAB_DOMAIN_NAME=" GITLAB_DOMAIN_NAME
read -rp "PROTON_EMAIL=" PROTON_EMAIL
read -rp "SMTP_TOKEN=" SMTP_TOKEN

tee -a /etc/gitlab/gitlab.rb >/dev/null <<EOF
 
external_url "https://${GITLAB_DOMAIN_NAME}"

gitlab_rails['smtp_enable'] = true
gitlab_rails['smtp_address'] = "smtp.protonmail.ch"
gitlab_rails['smtp_port'] = 587
gitlab_rails['smtp_authentication'] = "plain"
gitlab_rails['smtp_enable_starttls_auto'] = true
gitlab_rails['smtp_user_name'] = "${PROTON_EMAIL}"
gitlab_rails['smtp_password'] = "${SMTP_TOKEN}"
gitlab_rails['smtp_domain'] = "${GITLAB_DOMAIN_NAME}"
gitlab_rails['gitlab_email_from'] = "${PROTON_EMAIL}"
gitlab_rails['gitlab_email_reply_to'] = "${PROTON_EMAIL}"

registry_external_url "https://${GITLAB_DOMAIN_NAME}:5050"
EOF
#------------------------------------------------------------

gitlab-ctl reconfigure

curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.rpm.sh" -o script.rpm.sh
bash script.rpm.sh

echo "Login with these credentials:"
echo "Username: root"
echo "Password:"
cat /etc/gitlab/initial_root_password
read -rp "Press Enter to continue..."

dnf install -y gitlab-runner

echo "Create docker-runner on web console and paste the token here."
read -rp "RUNNER_TOKEN=" RUNNER_TOKEN

gitlab-runner register \
  --non-interactive \
  --url "https://${GITLAB_DOMAIN_NAME}" \
  --token "$RUNNER_TOKEN" \
  --executor "docker" \
  --docker-image alpine:latest \
  --description "docker-runner"

# STEP 1: Docker Registry
echo "Exchange 1: GitLab -> RKE2: Docker Registry"

# STEP 1.1: SSL Certificate
echo "Copy .crt content"
cat "/etc/gitlab/ssl/${GITLAB_DOMAIN_NAME}.crt"
read -rp "Press Enter to continue..."

# STEP 1.2:
echo "Group -> Settings -> Repository -> Deploy Tokens"
echo "Create deploy token on GitLab and copy content"

read -rp "Press Enter to continue..."

exit 0
#------------------------------------------------------------

# STEP 2: Kubernetes
# echo "Exchange 2: GitLab <- RKE2: Kube Config"
# .kube/config naar gitlab-runner user.
# van daar een docker rancher/kubectl runnen voor testing.
# als gelukt is het goed.
