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
- OpenSSL
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
├── .env                         # Environment variables (not committed)
├── .env.example                 # Example environment variables
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

Certificates are managed using Certbot and stored in `nginx/ssl/`.

**Structure:**
- `live/`: Current active certificates
- `archive/`: Historical certificate versions
- `renewal/`: Renewal configuration
- `renewal-hooks/`: Scripts that run during renewal (pre, post, deploy)

## Setup

### 1. Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env with your specific settings
```

### 2. SSL/TLS Certificates

Certificates are managed using Certbot and should be placed in `nginx/ssl/`.

Ensure the directory structure exists:

```bash
mkdir -p nginx/ssl/{live,archive,renewal,renewal-hooks/{pre,post,deploy}}
```

Place your certificate files in `nginx/ssl/live/` according to your domain configuration.

### 3. Authentication Credentials

Create basic authentication credentials using htpasswd:

```bash
mkdir -p nginx/auth
docker run --rm --entrypoint htpasswd httpd:2.4.66 -Bbn USERNAME PASSWORD > nginx/auth/registry.htpasswd
```

Replace `USERNAME` and `PASSWORD` with your desired credentials.

### 4. Start The Environment

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
