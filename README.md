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
  -out nginx/ssl/selfsigned.crt \
```

### htpasswd

`htpasswd` is used to generate the basic-auth credentials consumed by NGINX.

Expected file:

- `auth/nginx.htpasswd`

Example:

```bash
mkdir -p nginx/auth
sudo sh -c 'docker run --rm --entrypoint htpasswd httpd -Bbn <USERNAME> <PASSWORD> > nginx/auth/nginx.htpasswd'
```

### NGINX

NGINX listens on ports `80` and `443`.

- Port `80` redirects all traffic to HTTPS
- Port `443` terminates TLS
- Requests to `/v2/` are protected with basic auth
- Authenticated requests are proxied to the internal Docker Registry service

The active NGINX config is [nginx/conf.d/registry.conf](/home/max/Git/UMCU-AIResearch-SandboxEnvironment/nginx/conf.d/registry.conf).

### Registry

The backend service is the official Docker Registry image:

- Container image: `registry:3.0.0`
- Internal port: `5000`
- Persistent storage: Docker volume `registry_data`

The registry is not exposed directly to the host. Access goes through NGINX.

## Configuration

Set the hostname directly in the NGINX config:

```bash
edit nginx/conf.d/registry.conf
```

Update both `server_name` entries from `example.com` to the hostname you plan to use, for example `localhost`.

## Start The Environment

Run:

```bash
docker compose up -d
```

## How To Use The Registry

Log in:

```bash
docker login https://localhost
```

If you used a self-signed certificate, Docker may reject it until you trust the certificate on the host.

Tag an image:

```bash
docker tag alpine:latest localhost/alpine:latest
```

Push it:

```bash
docker push localhost/alpine:latest
```

Pull it:

```bash
docker pull localhost/alpine:latest
```

Replace `localhost` with the hostname configured in `nginx/conf.d/registry.conf` where applicable.
