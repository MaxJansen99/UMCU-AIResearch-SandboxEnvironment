# RKE2 Script

This document explains how `infrastructure/scripts/rke2.sh` works.

## Purpose

The script installs and configures a single-node RKE2 server on a RHEL-compatible host. It also configures RKE2/containerd to pull images from the GitLab container registry and prints kubeconfig content for use by GitLab Runner during the main install flow.

The script must be run as root for package installation, firewall changes, system configuration, and service management.

## Commands

```bash
sudo ./infrastructure/scripts/rke2.sh install
./infrastructure/scripts/rke2.sh help
```

If no command is provided, the script runs `install`.

## `install`

The `install` command runs the full RKE2 setup flow.

1. `install_prerequisites`
   - Installs `kernel-modules-extra`.

2. `configure_firewall`
   - Opens Kubernetes, etcd, NodePort, Canal, and WireGuard-related ports.
   - Reloads the firewall configuration.

3. `configure_network_manager`
   - Writes `/etc/NetworkManager/conf.d/rke2-canal.conf`.
   - Marks CNI interfaces such as `flannel*`, `cali*`, `vxlan.calico`, and WireGuard CNI interfaces as unmanaged by NetworkManager.
   - Reloads NetworkManager.

4. `write_rke2_config`
   - Prompts for `RKE2_DOMAIN_NAME`.
   - Writes `/etc/rancher/rke2/config.yaml`.
   - Adds the domain to `tls-san`.
   - Sets `write-kubeconfig-mode` to `0644`.
   - Adds the `role=single-node` node label.
   - Enables debug mode.

5. `configure_rke2_repository`
   - Writes the Rancher RKE2 yum repository file.
   - Uses `RKE2_MINOR=33` and `LINUX_MAJOR=10`.

6. `install_rke2_server`
   - Installs `rke2-server`.
   - Enables and starts `rke2-server.service`.

7. `configure_registry_access`
   - Prompts for `GITLAB_DOMAIN_NAME`.
   - Prompts you to paste the GitLab registry TLS certificate.
   - Prompts for:
     - `DEPLOY_NAME`
     - `DEPLOY_TOKEN`
   - Writes `/etc/rancher/rke2/registries.yaml`.
   - Restarts `rke2-server.service`.

8. `print_kubeconfig`
   - Creates `~/.kube`.
   - Copies `/etc/rancher/rke2/rke2.yaml` to `~/.kube/config`.
   - Updates the kubeconfig server address to the RKE2 domain name.
   - Prints the kubeconfig for the GitLab install flow.

## Manual Exchange With GitLab

The RKE2 and GitLab scripts are meant to be run as one guided install flow with two manual copy/paste exchanges.

### Exchange 1: GitLab registry to RKE2

First run the GitLab install flow on the GitLab host:

```bash
sudo ./infrastructure/scripts/gitlab.sh install
```

Copy these values from GitLab:

- GitLab registry TLS certificate.
- GitLab deploy token name.
- GitLab deploy token value.

Then run the RKE2 install flow on the RKE2 host:

```bash
sudo ./infrastructure/scripts/rke2.sh install
```

Paste the certificate and deploy token values when prompted.

The RKE2 install flow then prints the kubeconfig. Copy that output back into the waiting GitLab install flow and press `Ctrl-D` to finish input.

## Notes

- The RKE2 repository version is controlled by `RKE2_MINOR` and `LINUX_MAJOR` at the top of the script.
- The GitLab registry is expected to be available at `https://<gitlab-domain>:5050`.
- The deploy token is stored in `/etc/rancher/rke2/registries.yaml`, so protect access to that file.
- RKE2 utilities such as `kubectl`, `crictl`, and `ctr` are available in `/var/lib/rancher/rke2/bin`.
