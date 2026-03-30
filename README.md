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

## Creating a Self Signed Certificate

### Linux
For Redhat:
Go to commandline:
```json
 sudo mkdir -p nginx/ssl
 sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
 -keyout nginx/ssl/selfsigned.key \
 -out nginx/ssl/selfsigned.crt

 Fill in all the fields, if local for Common Name enter "localhost"
```
