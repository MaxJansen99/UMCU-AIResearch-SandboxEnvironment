# GPU Workload Templates

Reusable GitLab CI/CD, Docker, and Kubernetes templates for running GPU-enabled Python and TensorFlow workloads on Kubernetes.

This repository is intended to be included by user projects. A project keeps only its own source code, notebook, requirements, and small `.gitlab-ci.yml`; the shared build and deployment logic stays here.

## Description

The templates support a workflow where GitLab builds a container image, pushes it to the project container registry, and deploys it as a Kubernetes Job. The job runs either `main.ipynb` through Papermill or `main.py` with Python. Shared SMB storage is mounted into the workload so input data and generated output can live outside the container.

The repository also includes optional TensorBoard deployment manifests. TensorBoard reads from the same `G_Output` folder used by the training job and is exposed through a Kubernetes `NodePort` service.

## Repository Layout

```text
docker/
  python-gpu-environment/
    Dockerfile
  tensorflow-gpu-environment/
    Dockerfile

gitlab/
  shared/
    .gitlab-ci.yml
  python-gpu-environment/
    .gitlab-ci.yml
  tensorflow-gpu-environment/
    .gitlab-ci.yml
  docker-gpu-environment/
    .gitlab-ci.yml

kubernetes/
  gpu-environment/
    deployment.yml
    job.yml
    pv.yml
    pvc.yml
    service.yml

docs/
  latex/
    TechnicalDocumentation.tex
    TechnicalDocumentation.pdf
```

## Templates

### Python GPU Environment

Use this when the project provides a `requirements.txt` and should run in a CUDA-enabled Python image.

```yaml
include:
  - project: "${CI_PROJECT_NAMESPACE}/templates"
    file: /gitlab/python-gpu-environment/.gitlab-ci.yml
```

Expected project files:

```text
requirements.txt
main.py
```

or:

```text
requirements.txt
main.ipynb
```

### TensorFlow GPU Environment

Use this when the project should run with a prebuilt TensorFlow, Jupyter, Papermill, NumPy, Pandas, Matplotlib, and TensorBoard environment.

```yaml
include:
  - project: "${CI_PROJECT_NAMESPACE}/templates"
    file: /gitlab/tensorflow-gpu-environment/.gitlab-ci.yml
```

Expected project files:

```text
main.py
```

or:

```text
main.ipynb
```

### Custom Docker GPU Environment

Use this when the project provides its own `Dockerfile` but should still use the shared build and Kubernetes deployment pipeline.

```yaml
include:
  - project: "${CI_PROJECT_NAMESPACE}/templates"
    file: /gitlab/docker-gpu-environment/.gitlab-ci.yml
```

Expected project files:

```text
Dockerfile
main.py
```

or:

```text
Dockerfile
main.ipynb
```

## Pipeline Behavior

The shared GitLab pipeline has three stages:

1. `build`: builds a Docker image with Docker-in-Docker and pushes it to the project container registry.
2. `deploy`: creates or updates the SMB-backed PersistentVolume and PersistentVolumeClaim, then deploys a Kubernetes Job.
3. `log`: contains reusable hidden jobs for TensorBoard and training logs.

The Kubernetes Job requests one NVIDIA GPU:

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"
```

The workload command checks for `main.ipynb` first. If it exists, the notebook is executed with Papermill and written to `G_Output/notebooks/executed-main.ipynb`. If no notebook exists, the job runs `main.py`.

## Required CI/CD Variables

Set these variables in the user project or group before running the pipeline.

| Variable | Description |
| --- | --- |
| `KUBECONFIG` | Kubernetes configuration available to the GitLab job. |
| `K8S_IMAGE_PULL_SECRET` | Kubernetes image pull secret used by the workload pods. |
| `SMB_SOURCE` | SMB share source used by the CSI PersistentVolume, for example `//server/share`. |
| `SMB_USERNAME` | Username for the SMB share. |
| `SMB_PASSWORD` | Password for the SMB share. |
| `SMB_DOMAIN` | Optional SMB domain. |
| `STUDY_FOLDER` | Folder inside the SMB share mounted by the workload. |

Optional variables:

| Variable | Default | Description |
| --- | --- | --- |
| `NOTEBOOK_KERNEL` | `python3` | Kernel used when executing `main.ipynb`. |
| `TENSORBOARD_HOST` | Derived from the Kubernetes server URL | Host used to build the GitLab TensorBoard environment URL. |

## Storage Layout

The Kubernetes manifests mount the SMB share through a PersistentVolumeClaim and use `STUDY_FOLDER` to select the study-specific folder.

Inside the container:

| Container path | SMB path | Access |
| --- | --- | --- |
| `/app/E_ResearchData` | `${STUDY_FOLDER}/E_ResearchData` | Read-only |
| `/app/G_Output` | `${STUDY_FOLDER}/G_Output` | Read-write |

Place input data in `E_ResearchData`. Write generated files, logs, executed notebooks, and TensorBoard output to `G_Output`.

## Usage

Create a GitLab project for the workload and add the template include that matches the project.

Minimal TensorFlow notebook project:

```text
.gitlab-ci.yml
main.ipynb
```

`.gitlab-ci.yml`:

```yaml
include:
  - project: "${CI_PROJECT_NAMESPACE}/templates"
    file: /gitlab/tensorflow-gpu-environment/.gitlab-ci.yml
```

Minimal Python project with dependencies:

```text
.gitlab-ci.yml
requirements.txt
main.py
```

`.gitlab-ci.yml`:

```yaml
include:
  - project: "${CI_PROJECT_NAMESPACE}/templates"
    file: /gitlab/python-gpu-environment/.gitlab-ci.yml
```

After committing and pushing the project, GitLab starts the pipeline. The built image is tagged with the commit short SHA and deployed as a Kubernetes Job named:

```text
<project-name>-job
```

## TensorBoard

The shared pipeline defines a hidden `.tensorboard` job. A user project can expose it by extending the job:

```yaml
tensorboard:
  extends: .tensorboard
```

TensorBoard serves `/app/G_Output` on port `6006`. The pipeline stores the generated NodePort URL as a GitLab dotenv artifact so it can be shown as a GitLab environment URL.

## Documentation

Detailed infrastructure documentation is available in:

- `docs/latex/TechnicalDocumentation.tex`
- `docs/latex/TechnicalDocumentation.pdf`

That document covers the GitLab, RKE2, SMB, runner, Kubernetes, registry, and user workflow setup in more detail.

## Contributing

Keep shared behavior in `gitlab/shared/.gitlab-ci.yml` and only put template-specific overrides in the template entry points under `gitlab/*/.gitlab-ci.yml`.

When changing Kubernetes manifests, keep the required environment variables explicit because they are rendered with `envsubst` during the deployment job.

## Project Status

This repository contains proof-of-concept infrastructure templates for GPU workload deployment. Review sizing, security, backups, monitoring, access control, and production hardening before using these templates in a production environment.
