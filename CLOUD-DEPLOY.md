# Cloud Deployment Guide — AWS Lightsail

This app runs on the same Lightsail instance as the Streaming Tracker, routed
by subdomain via host-level nginx.

**AWS Profile**: `reveller-20250816`
**Region**: `us-east-1` (Virginia)
**Domain**: `vocab.n2deep.co`
**Instance**: `streaming-tracker` (shared with Streaming Tracker)
**Static IP**: `<STATIC_IP>`

---

## Overview

```
┌─────────────────────────────────────────────────────────┐
│  Lightsail Instance (Ubuntu 22.04)                      │
│                                                         │
│  Host nginx (:80/:443)                                  │
│    ├─ tracker.n2deep.co → Streaming Tracker (:8080)     │
│    └─ vocab.n2deep.co   → Spanish Vocab     (:5050)     │
│                                                         │
│  ┌──────────────────┐                                   │
│  │  Spanish Vocab   │  Gunicorn + Flask + SQLite        │
│  │  (Docker :5050)  │  Data volume: vocab-data → /data  │
│  └──────────────────┘                                   │
│                                                         │
│  SSL: Let's Encrypt (shared cert for both subdomains)   │
└─────────────────────────────────────────────────────────┘
```

---

## SSH Access

```bash
ssh -i ~/.ssh/lightsail-streaming.pem ubuntu@<STATIC_IP>
```

---

## Initial Setup (Already Complete)

These steps document how the app was deployed for reference.

### 1. DNS

Added an **A record** for `vocab` in GoDaddy DNS for `n2deep.co` pointing to `<STATIC_IP>`.

### 2. Clone and Configure

```bash
cd /home/ubuntu
git clone https://github.com/reveller/spanish-vocab.git
cd spanish-vocab

# Create .env with a generated secret key
cat > .env << 'EOF'
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_hex(32))">
SEED_USER_EMAIL=<email>
SEED_USER_PASSWORD=<password>
EOF
```

### 3. Start the App

```bash
docker compose up -d --build
```

### 4. Nginx Reverse Proxy

Created `/etc/nginx/sites-available/vocab.n2deep.co`:

```nginx
server {
    listen 80;
    server_name vocab.n2deep.co;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name vocab.n2deep.co;

    ssl_certificate /etc/letsencrypt/live/tracker.n2deep.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tracker.n2deep.co/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/vocab.n2deep.co /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 5. Remove Seed Credentials

After the first run, `SEED_USER_EMAIL` and `SEED_USER_PASSWORD` were removed
from `.env`. The user is stored in SQLite and persists via the Docker volume.

---

## SSL Certificate

Both subdomains share a single Let's Encrypt certificate:

```
Certificate Name: tracker.n2deep.co
Domains: tracker.n2deep.co vocab.n2deep.co
Path: /etc/letsencrypt/live/tracker.n2deep.co/
```

---

## Deploying Updates

```bash
ssh -i ~/.ssh/lightsail-streaming.pem ubuntu@<STATIC_IP>
cd /home/ubuntu/spanish-vocab
git pull
docker compose up -d --build
```

If Docker caches layers and skips code changes:

```bash
docker compose build --no-cache && docker compose up -d
```

---

## Logs

The app logs auth events and data mutations to stdout, captured by Docker.

**Events logged:**

| Level | Event | Details |
|-------|-------|---------|
| WARNING | Login failed | email, IP |
| WARNING | Unauthorized API access | method, path, IP |
| INFO | Login success | email, IP |
| INFO | Logout | email, IP |
| INFO | Lesson created/deleted | lesson ID, title, user |
| INFO | Word added/deleted | word details, lesson, user |

**Viewing logs (from the instance):**

```bash
# Tail all logs in real time
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml logs -f

# Last 50 lines
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml logs --tail 50

# Filter for login failures
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml logs | grep "Login failed"

# Filter for all auth events (login/logout/unauthorized)
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml logs | grep -E "Login|Logout|Unauthorized"
```

**Viewing logs (from your local machine):**

```bash
ssh -i ~/.ssh/lightsail-streaming.pem ubuntu@<STATIC_IP> \
  "docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml logs -f"
```

**Nginx access logs** (all HTTP requests, including IPs and status codes):

```bash
# Tail nginx access log
sudo tail -f /var/log/nginx/access.log

# Filter for vocab subdomain
sudo grep "vocab.n2deep.co" /var/log/nginx/access.log

# Nginx error log
sudo tail -f /var/log/nginx/error.log
```

> **Note**: Docker logs reset when the container is recreated (`docker compose up -d --build`).
> Nginx logs are rotated automatically by logrotate on the host.

---

## Useful Commands

```bash
# View container status
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml ps

# Restart
docker compose -f /home/ubuntu/spanish-vocab/docker-compose.yml restart

# Health check
curl -s http://localhost:5050/api/health
```

---

## Environment Variables

| Variable | Where | Description |
|----------|-------|-------------|
| `SECRET_KEY` | `.env` | Flask session signing key |
| `DATABASE_PATH` | `docker-compose.yml` | Path to SQLite DB inside container (`/data/vocab.db`) |
| `SEED_USER_EMAIL` | `.env` (first run only) | Email for initial user |
| `SEED_USER_PASSWORD` | `.env` (first run only) | Password for initial user |

---

## Rollback

To remove the vocab app from the instance without affecting the streaming tracker:

```bash
ssh -i ~/.ssh/lightsail-streaming.pem ubuntu@<STATIC_IP>

# Stop and remove containers/volumes
cd /home/ubuntu/spanish-vocab
docker compose down -v

# Remove nginx config
sudo rm /etc/nginx/sites-enabled/vocab.n2deep.co
sudo rm /etc/nginx/sites-available/vocab.n2deep.co
sudo nginx -t && sudo systemctl reload nginx

# Remove the repo
rm -rf /home/ubuntu/spanish-vocab
```

Then remove the `vocab` A record from GoDaddy DNS.
