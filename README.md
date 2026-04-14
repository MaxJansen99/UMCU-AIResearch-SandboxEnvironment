# UMCU AI Research Sandbox Environment

## Description

This repository provides a private Docker Registry infrastructure with secure access controls. The environment consists of:

- **Docker Registry**: A containerized private registry for storing and managing Docker images
- **NGINX Reverse Proxy**: Acts as the front-facing server with HTTPS termination and basic authentication
- **SSL/TLS Support**: Configured for encrypted communication
- **Basic Authentication**: Protects registry access using htpasswd credentials
- **Persistent Storage**: Registry data persists across container restarts

The setup is designed for internal use within the UMCU AI Research project and can be deployed for development, testing, and production sandbox environments.

## Prerequisites

Before starting the environment, make sure the following are available:

- Docker Engine
- Docker Compose

- `htpasswd` from Apache Httpd
- Access to ports `80` and `443` on the host machine

### Docker group

Make sure your user is part of the `docker` group, so Docker commands can be run without `sudo`:

```bash
sudo usermod -aG docker $USER
```

This updates your group membership for the current shell. If that does not work, log out and back in again.

## Project Structure

```
├── docker-compose.yaml          # Main Docker Compose configuration
├── README.md                    # This file
├── nginx/                       # NGINX configuration
│   ├── conf.d/                 # NGINX server blocks
│   │   ├── local.conf          # Default localhost NGINX config
│   │   └── production.conf     # Production domain NGINX config
│   ├── auth/                   # Basic authentication credentials
│   └── ssl/                    # SSL/TLS certificates and keys
└── registry/                    # Docker Registry configuration
    └── config.yaml             # Registry configuration file
```

## Components

### Docker Registry

The backend service uses the official Docker Distribution (Registry) image.

**Configuration:**

- Container image: `registry:3.0.0`
- Internal port: `5000` (not exposed to host)
- Configuration file: `registry/config.yaml`
- Persistent storage: Docker volume `registry_data`

The registry is not directly accessible from the host. All access must go through the NGINX reverse proxy.

### NGINX Reverse Proxy

NGINX serves as the entry point and reverse proxy for the registry.

**Configuration:**

- Container image: `nginx:1.29.7`
- Exposed ports: `80` (HTTP), `443` (HTTPS)
- Configuration files: `nginx/conf.d/local.conf` and `nginx/conf.d/production.conf`
- Authentication: `nginx/auth/registry.htpasswd`
- SSL certificates: `nginx/ssl/` (Certbot-managed)

**Features:**

- Port `80` redirects all traffic to HTTPS (`443`)
- TLS termination on port `443`
- `/v2/` API endpoints protected with basic authentication
- Non-authenticated requests proxied to the Docker Registry

### SSL/TLS Certificates

Certificates can be managed using Certbot (for production with domain) or self-signed certificates (for local development).

**Structure:**

- `live/`: Current active certificates
- `archive/`: Historical certificate versions
- `renewal/`: Renewal configuration
- `renewal-hooks/`: Scripts that run during renewal (pre, post, deploy)

#### For Local Development (Self-Signed Certificates)

If you don't have a domain or want to test locally, use a self-signed certificate for `localhost`. The setup steps are listed in [Setup](#setup).

For Docker clients, prefer configuring the registry as insecure instead of copying the self-signed certificate into Docker's trust store. The exact steps are documented in [How To Use The Registry](#how-to-use-the-registry).

## Setup

### 1. SSL/TLS Certificates

The Docker Compose file is set up for **localhost development by default**. For production with a domain, you need to switch the mounted NGINX config in `docker-compose.yaml`.

#### Option A: Local Development (Default - Recommended)

```bash
# Generate self-signed certificates for localhost
mkdir -p nginx/ssl/live/localhost
docker run --rm \
  -v "$(pwd)/nginx/ssl/live/localhost:/certs" \
  alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /certs/privkey.pem \
  -out /certs/fullchain.pem \
  -subj "/CN=localhost"
```

`docker-compose.yaml` already mounts `nginx/conf.d/local.conf` by default, so no Compose changes are needed for localhost.

#### Option B: Production with Domain

If you have a real domain and want to use Certbot:

1. **Generate Certbot certificates:**

```bash
mkdir -p nginx/ssl
docker run --rm \
  -v "$(pwd)/nginx/ssl:/etc/letsencrypt" \
  -p 80:80 \
  certbot/certbot:v5.5.0 certonly \
  --standalone \
  --agree-tos \
  --email your-email@example.com \
  -d your-domain.com
```

2. **Update the production NGINX config:**
   - Edit `nginx/conf.d/production.conf`
   - Replace `your-domain.com` with your real domain
   - Verify the certificate paths match your Certbot output

3. **Switch Docker Compose to production:**
   - Edit `docker-compose.yaml`
   - Replace the `local.conf` volume mount with `production.conf`
   - Keep only one of the two mounts enabled at a time

### 2. Authentication Credentials

Create basic authentication credentials using htpasswd:

```bash
mkdir -p nginx/auth
docker run --rm --entrypoint htpasswd httpd:2.4.66 -Bbn USERNAME PASSWORD > nginx/auth/registry.htpasswd
```

Replace `USERNAME` and `PASSWORD` with your desired credentials.

### 3. Start The Environment

Start all services with Docker Compose:

```bash
docker compose up -d
```

To view logs:

```bash
docker compose logs -f
```

To stop the environment:

```bash
docker compose down
```

## How To Use The Registry

### On Localhost (for Development) - DEFAULT SETUP

After generating the self-signed certificates, configure Docker to allow the local registry:

```bash
sudo mkdir -p /etc/docker
```

Edit `/etc/docker/daemon.json` and add:

```json
{
  "insecure-registries": ["localhost"]
}
```

If the file already exists, merge the `insecure-registries` entry into the existing JSON instead of replacing the whole file.

Restart Docker:

```bash
sudo systemctl restart docker
```

After that:

**Log in:**

```bash
docker login localhost
```

**Tag an image:**

```bash
docker tag my-image:latest localhost/my-image:latest
```

**Push the image:**

```bash
docker push localhost/my-image:latest
```

**Pull the image:**

```bash
docker pull localhost/my-image:latest
```

If you still get certificate errors on localhost, confirm that Docker picked up the `insecure-registries` setting and that the daemon was restarted after editing `/etc/docker/daemon.json`.

### On Production Server (with Domain)

After setting up with Certbot certificates and switching `docker-compose.yaml` to `nginx/conf.d/production.conf`:

**Log in:**

```bash
docker login your-domain.com
```

**Tag an image:**

```bash
docker tag my-image:latest your-domain.com/my-image:latest
```

**Push the image:**

```bash
docker push your-domain.com/my-image:latest
```

**Pull the image (from another machine):**

```bash
docker pull your-domain.com/my-image:latest
```
