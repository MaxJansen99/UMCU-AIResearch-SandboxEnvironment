# GitLab Script

This document explains how `infrastructure/scripts/gitlab.sh` works.

## Purpose

The script installs and configures GitLab CE, Docker, and GitLab Runner on a RHEL-compatible host. It also prints the information that must be copied to the RKE2 host so RKE2 can trust and use the GitLab container registry.

The script must be run as root for the commands that install packages, change firewall rules, write system configuration, and restart services.

## Commands

```bash
sudo ./infrastructure/scripts/gitlab.sh install
sudo ./infrastructure/scripts/gitlab.sh kube-config
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

## `kube-config`

The `kube-config` command configures GitLab Runner so CI jobs can access the RKE2 cluster.

It does the following:

1. Creates `/home/gitlab-runner/.kube`.
2. Prompts you to paste kubeconfig content from the RKE2 host.
3. Writes that content to `/home/gitlab-runner/.kube/config` as the `gitlab-runner` user.
4. Updates `/etc/gitlab-runner/config.toml` so Docker jobs mount the kubeconfig read-only at `/root/.kube`.
5. Restarts GitLab Runner.

Run this after the RKE2 host has produced its kubeconfig with:

```bash
sudo ./infrastructure/scripts/rke2.sh kube-config
```

## Manual Exchange With RKE2

The GitLab and RKE2 scripts are meant to be run in two exchange steps.

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

### Exchange 2: RKE2 kubeconfig to GitLab

On the RKE2 host:

```bash
sudo ./infrastructure/scripts/rke2.sh kube-config
```

Copy the kubeconfig output and update the server address to the RKE2 domain name when needed.

On the GitLab host:

```bash
sudo ./infrastructure/scripts/gitlab.sh kube-config
```

Paste the kubeconfig content and press `Ctrl-D` to finish input.

## Notes

- The script appends to `/etc/gitlab/gitlab.rb`; running it multiple times can duplicate configuration blocks.
- The runner registration expects that the runner token was created in the GitLab web console first.
- The kubeconfig mount replaces the first `volumes = [` line in `/etc/gitlab-runner/config.toml`.
