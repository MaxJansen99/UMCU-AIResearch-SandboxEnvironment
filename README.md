# UMCU-AIResearch-SandboxEnvironment

Minimal local sandbox environment for AI research workflows.

## Docker

If you use a local Docker registry on `localhost`, add `localhost` to Docker's insecure registries before starting the environment.

### Windows

Docker Desktop:

```json
{
  "insecure-registries": ["localhost"]
}
```

### macOS

Docker Desktop:

```json
{
  "insecure-registries": ["localhost"]
}
```

### Linux

Edit `/etc/docker/daemon.json`:

```json
{
  "insecure-registries": ["localhost"]
}
```

Then restart Docker.
