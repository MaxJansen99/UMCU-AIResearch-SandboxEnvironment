# UMCU AI Research Sandbox Environment

## Table of Contents

- [Description](#description)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
    - [SSL/TLS Certificates](#ssltls-certificates)
    - [Authentication Credentials](#authentication-credentials)
    - [Start The Environment](#start-the-environment)
- [Usage Guide](#usage-guide)
  - [On Localhost (for Development)](#on-localhost-for-development)
  - [On Production Server (with Domain)](#on-production-server-with-domain)

## Description

This repository provides a private Docker Registry infrastructure with secure access controls. The environment consists of:

- **Docker Registry**: A containerized private registry for storing and managing Docker images
- **NGINX Reverse Proxy**: Acts as the front-facing server with HTTPS termination and basic authentication
- **SSL/TLS Support**: Configured for encrypted communication
- **Basic Authentication**: Protects registry access using htpasswd credentials
- **Persistent Storage**: Registry data persists across container restarts

The setup is designed for internal use within the UMCU AI Research project and can be deployed for development, testing, and production sandbox environments.

## Installation

### Prerequisites

Before starting the environment, make sure the following are available:

- Docker Engine
- Docker Compose
- `htpasswd` from Apache Httpd
- Access to ports `80` and `443` on the host machine

### Installation Instructions

#### Windows

1. **Install Docker Desktop**:
   - Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - Ensure WSL 2 backend is enabled

2. **Install OpenSSL**:
   - Download and install OpenSSL from [SLProWeb](https://slproweb.com/products/Win32OpenSSL.html)
   - Add OpenSSL to your system PATH

3. **Install htpasswd**:
   - Use WSL or install Apache HTTP Server from [Apache Lounge](https://www.apachelounge.com/)

#### macOS

1. **Install Docker Desktop**:
   - Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)

2. **Install OpenSSL**:
   - Already included in macOS, but you can install the latest version via Homebrew:

   ```bash
   brew install openssl
   ```

3. **Install htpasswd**:
   - Install via Homebrew:

   ```bash
   brew install httpd
   ```

#### Linux

1. **Install Docker Engine**:
   - Follow the official Docker installation guide for your distribution:
   - [Ubuntu/Debian](https://docs.docker.com/engine/install/ubuntu/)
   - [RedHat/Fedora](https://docs.docker.com/engine/install/fedora/)
   - [Other distributions](https://docs.docker.com/engine/install/)

2. **Install OpenSSL**:

   ```bash
   # Ubuntu/Debian
   sudo apt-get install openssl
   
   # RedHat/Fedora
   sudo dnf install openssl
   ```

3. **Install htpasswd**:

   ```bash
   # Ubuntu/Debian
   sudo apt-get install apache2-utils
   
   # RedHat/Fedora
   sudo dnf install httpd-tools
   ```

4. **Add user to docker group**:

   ```bash
   sudo usermod -aG docker $USER
   ```

   Log out and back in for the changes to take effect.

### Docker group

Make sure your user is part of the `docker` group, so Docker commands can be run without `sudo`:

```bash
sudo usermod -aG docker $USER
```

This updates your group membership for the current shell. If that does not work, log out and back in again.

### Setup

#### SSL/TLS Certificates

The Docker Compose file is set up for **localhost development by default**. For production with a domain, you need to switch the mounted NGINX config in `docker-compose.yaml`.

##### Option A: Local Development

```bash
# Generate self-signed certificates for localhost
mkdir -p nginx/ssl/live/localhost
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/live/localhost/privkey.pem \
  -out nginx/ssl/live/localhost/fullchain.pem \
  -subj "/CN=localhost"
```

`docker-compose.yaml` already mounts `nginx/conf.d/local.conf` by default, so no Compose changes are needed for localhost.

##### Option B: Production with Domain

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
  --email email@example.com \
  -d production.example.com
```

1. **Update the production NGINX config:**
   - Edit `nginx/conf.d/production.conf`
   - Replace `email@example.com` with your real email
   - Replace `production.example.com` with your real domain
   - Verify the certificate paths match your Certbot output

2. **Switch Docker Compose to production:**
   - Edit `docker-compose.yaml`
   - Replace the `local.conf` volume mount with `production.conf`
   - Keep only one of the two mounts enabled at a time

#### Authentication Credentials

Create basic authentication credentials using htpasswd:

```bash
mkdir -p nginx/auth
htpasswd -Bbn USERNAME PASSWORD > nginx/auth/registry.htpasswd
```

Replace `USERNAME` and `PASSWORD` with your desired credentials.

#### Start The Environment

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

## Usage Guide

### On Localhost

After generating the self-signed certificates, configure Docker to allow the local registry:

```bash
sudo mkdir -p /etc/docker
```

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

### On Production Server

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

**Pull the image:

```bash
docker pull your-domain.com/my-image:latest
```
