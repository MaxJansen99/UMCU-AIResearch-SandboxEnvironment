# GitLab Script

This document explains how `infrastructure/scripts/gitlab.sh` works.

## Purpose

The script installs and configures GitLab CE, Docker, and GitLab Runner on a RHEL-compatible host. It also prints the information that must be copied to the RKE2 host so RKE2 can trust and use the GitLab container registry, then prompts for the RKE2 kubeconfig during the main install flow.

The script must be run as root for the commands that install packages, change firewall rules, write system configuration, and restart services.

## Commands

```bash
sudo ./infrastructure/scripts/gitlab.sh install
./infrastructure/scripts/gitlab.sh help
```

If no command is provided, the script runs `install`.

## `install`

The `install` command runs the full GitLab setup flow.

1. `install_docker`
   - Installs `dnf-plugins-core`.
   - Adds the Docker repository.
   - Installs Docker Engine, Docker CLI, containerd, Buildx, and Compose.
   - Enables and starts `docker.service`.

2. `configure_firewall`
   - Opens ports `22`, `80`, `443`, and `5050`.
   - Port `5050` is used for the GitLab container registry.

3. `install_gitlab_ce`
   - Installs `curl`.
   - Adds the GitLab CE package repository.
   - Installs `gitlab-ce`.

4. `configure_gitlab`
   - Prompts for:
     - `GITLAB_DOMAIN_NAME`
     - `PROTON_EMAIL`
     - `SMTP_TOKEN`
   - Appends GitLab external URL, SMTP settings, sender settings, and registry URL to `/etc/gitlab/gitlab.rb`.
   - Runs `gitlab-ctl reconfigure`.

5. `install_gitlab_runner`
   - Adds the GitLab Runner repository.
   - Prints the initial GitLab root password from `/etc/gitlab/initial_root_password`.
   - Installs `gitlab-runner`.

6. `register_docker_runner`
   - Prompts for `RUNNER_TOKEN`.
   - Registers a Docker executor runner using `alpine:latest`.

7. `show_registry_exchange`
   - Prints the GitLab registry TLS certificate from `/etc/gitlab/ssl/<domain>.crt`.
   - Pauses so you can copy the certificate to the RKE2 install flow.
   - Reminds you to create and copy a GitLab deploy token.

8. `configure_runner_kubeconfig`
   - Creates `/home/gitlab-runner/.kube`.
   - Prompts you to paste kubeconfig content from the RKE2 host.
   - Writes that content to `/home/gitlab-runner/.kube/config` as the `gitlab-runner` user.
   - Updates `/etc/gitlab-runner/config.toml` so Docker jobs mount the kubeconfig read-only at `/root/.kube`.
   - Restarts GitLab Runner.

## Manual Exchange With RKE2

The GitLab and RKE2 scripts are meant to be run as one guided install flow with two manual copy/paste exchanges.

### Exchange 1: GitLab registry to RKE2

On the GitLab host:

```bash
sudo ./infrastructure/scripts/gitlab.sh install
```

Copy these values when the script asks:

- The GitLab registry TLS certificate.
- A GitLab deploy token name.
- A GitLab deploy token value.

Paste those values into the RKE2 install flow.

The GitLab install flow then waits for kubeconfig content. Run the RKE2 install flow on the RKE2 host, copy the kubeconfig it prints at the end, paste it into the waiting GitLab install flow, and press `Ctrl-D` to finish input.

## Notes

- The script appends to `/etc/gitlab/gitlab.rb`; running it multiple times can duplicate configuration blocks.
- The runner registration expects that the runner token was created in the GitLab web console first.
- The kubeconfig mount replaces the first `volumes = [` line in `/etc/gitlab-runner/config.toml`.
