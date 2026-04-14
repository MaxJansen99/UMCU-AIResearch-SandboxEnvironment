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
- Configuration: `nginx/conf.d/registry.conf`
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

If you don't have a domain or want to test locally, you can generate self-signed certificates for localhost using Docker:

```bash
mkdir -p nginx/ssl/live/localhost
docker run --rm \
  -v "$(pwd)/nginx/ssl/live/localhost:/certs" \
  alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /certs/privkey.pem \
  -out /certs/fullchain.pem \
  -subj "/CN=localhost"
```

The NGINX configuration already includes a localhost server block that will automatically use these certificates. No additional configuration is needed.

**Note:** You'll need to trust the self-signed certificate in your Docker client or use `--insecure-registry` flag:

```bash
# For Docker to trust the self-signed certificate
mkdir -p /etc/docker/certs.d/localhost
cp nginx/ssl/live/localhost/fullchain.pem /etc/docker/certs.d/localhost/ca.crt

# Then restart Docker
sudo systemctl restart docker
```

Alternatively, you can use the `--insecure-registry` flag when starting Docker.

## Setup

### 1. SSL/TLS Certificates

The NGINX configuration is set up for **localhost development by default**. For production with a domain, you'll need to uncomment the production server block.

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

The NGINX configuration already has localhost enabled - no changes needed!

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

2. **Enable the production server block:**
   - Edit `nginx/conf.d/registry.conf`
   - Uncomment the production server block (remove the `/*` and `*/` comments)
   - Update the server_name to your domain
   - Update the certificate paths to match your domain

3. **Disable localhost (optional):**
   - You can comment out or remove the localhost server block if you only want production

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

After setting up with self-signed certificates:

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

**Troubleshooting localhost:**
If you get certificate errors, you have three options:

1. **Trust the certificate (recommended):**
```bash
sudo mkdir -p /etc/docker/certs.d/localhost
sudo cp nginx/ssl/live/localhost/fullchain.pem /etc/docker/certs.d/localhost/ca.crt
sudo systemctl restart docker
```

2. **Use insecure registry flag:**
```bash
# Add this to your Docker daemon startup or config
dockerd --insecure-registry localhost
```

3. **Edit Docker daemon config:**
```bash
# Edit /etc/docker/daemon.json and add:
{
  "insecure-registries" : ["localhost"]
}
# Then restart Docker
sudo systemctl restart docker
```

### On Production Server (with Domain)

After setting up with Certbot certificates and uncommenting the production server block:

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
