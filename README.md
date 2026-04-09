# Docker Registry Sandbox Environment

## Description

This repository provides a private Docker Registry behind NGINX with:

- HTTPS termination using a self-signed OpenSSL certificate
- Basic authentication using an `htpasswd` file
- An NGINX reverse proxy in front of the Docker Registry
- Persistent registry storage through a Docker volume

The setup is intended for local development, testing, and internal sandbox use.

## Components

### OpenSSL

OpenSSL is used to generate the TLS certificate and private key used by NGINX.

Expected files:

- `nginx/ssl/selfsigned.crt`
- `nginx/ssl/selfsigned.key`

Example:

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/selfsigned.key \
  -out nginx/ssl/selfsigned.crt
```

### Docker group

Make sure your user is part of the `docker` group, so Docker commands can be run without `sudo`:

```bash
sudo usermod -aG docker $USER
```

This updates your group membership for the current shell. If that does not work, log out and back in again.

### htpasswd

`htpasswd` is used to generate the basic-auth credentials consumed by NGINX.

Expected file:

- `auth/nginx.htpasswd`

Example:

```bash
mkdir -p nginx/auth
docker run --rm --entrypoint htpasswd httpd:2.4.66-Bbn <USERNAME> <PASSWORD> > nginx/auth/nginx.htpasswd
```

### Registry

The backend service is the official Docker Registry image:

- Container image: `registry:3.0.0`
- Internal port: `5000`
- Persistent storage: Docker volume `registry_data`

The registry is not exposed directly to the host. Access goes through NGINX.

### NGINX

NGINX listens on ports `80` and `443`.

- Port `80` redirects all traffic to HTTPS
- Port `443` terminates TLS
- Requests to `/v2/` are protected with basic auth
- Authenticated requests are proxied to the internal Docker Registry service

## Logging

Create the directory for nginx logs

```bash
mkdir -p nginx/logs
```

## Start The Environment

Run:

```bash
docker compose up -d
```

## How To Use The Registry

Log in:

```bash
docker login localhost
```

Tag an image:

```bash
docker tag image:latest localhost/image:latest
```

Push it:

```bash
docker push localhost/image:latest
```

Pull it:

```bash
docker pull localhost/image:latest
```
