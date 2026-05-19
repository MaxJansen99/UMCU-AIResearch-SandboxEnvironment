#!/usr/bin/env bash
set -euo pipefail

readonly DEFAULT_MODE="install"

usage() {
  cat <<'EOF'
Usage:
  ./gitlab.sh [install|kube-config|help]

Commands:
  install      Install Docker, GitLab CE, GitLab Runner and prepare registry exchange.
  kube-config  Add a kubeconfig for gitlab-runner and mount it in runner config.
  help         Show this help text.
EOF
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root." >&2
    exit 1
  fi
}

pause() {
  read -rp "Press Enter to continue..."
}

install_docker() {
  dnf -y install dnf-plugins-core
  dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
  dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker.service
}

configure_firewall() {
  firewall-cmd --permanent --add-port=22/tcp
  firewall-cmd --permanent --add-port=80/tcp
  firewall-cmd --permanent --add-port=443/tcp
  firewall-cmd --permanent --add-port=5050/tcp
  firewall-cmd --reload
}

install_gitlab_ce() {
  dnf install -y curl
  curl --location "https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.rpm.sh" | bash
  dnf install -y gitlab-ce
}

configure_gitlab() {
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

  gitlab-ctl reconfigure
}

install_gitlab_runner() {
  curl -L "https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.rpm.sh" -o script.rpm.sh
  bash script.rpm.sh

  echo "Login with these credentials:"
  echo "Username: root"
  echo "Password:"
  cat /etc/gitlab/initial_root_password
  pause

  dnf install -y gitlab-runner
}

register_docker_runner() {
  echo "Create docker-runner on web console and paste the token here."
  read -rp "RUNNER_TOKEN=" RUNNER_TOKEN

  gitlab-runner register \
    --non-interactive \
    --url "https://${GITLAB_DOMAIN_NAME}" \
    --token "${RUNNER_TOKEN}" \
    --executor "docker" \
    --docker-image alpine:latest \
    --description "docker-runner"
}

show_registry_exchange() {
  echo "Exchange 1: GitLab -> RKE2: Docker Registry"

  # STEP 1.1: SSL certificate for the RKE2 registry trust configuration.
  echo "Copy .crt content"
  cat "/etc/gitlab/ssl/${GITLAB_DOMAIN_NAME}.crt"
  pause

  # STEP 1.2: GitLab deploy token is copied manually to the RKE2 script.
  echo "Group -> Settings -> Repository -> Deploy Tokens"
  echo "Create deploy token on GitLab and copy content"
  pause
}

install_all() {
  install_docker
  configure_firewall
  install_gitlab_ce
  configure_gitlab
  install_gitlab_runner
  register_docker_runner
  show_registry_exchange
}

configure_runner_kubeconfig() {
  echo "Exchange 2: GitLab <- RKE2: Kube Config"

  sudo -u gitlab-runner mkdir -p /home/gitlab-runner/.kube
  echo "Paste .kube/config content, then press Ctrl-D:"
  sudo -u gitlab-runner tee "/home/gitlab-runner/.kube/config" >/dev/null

  # Mount kubeconfig read-only into Docker runner jobs.
  sudo sed -i '/^\s*volumes = \[/c\    volumes = ["/cache", "/home/gitlab-runner/.kube:/root/.kube:ro"]' /etc/gitlab-runner/config.toml
  gitlab-runner restart
}

main() {
  local mode="${1:-${DEFAULT_MODE}}"

  case "${mode}" in
    install)
      require_root
      install_all
      ;;
    kube-config)
      require_root
      configure_runner_kubeconfig
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
