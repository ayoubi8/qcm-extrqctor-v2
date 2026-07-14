# Ubuntu VPS Backend Runbook

Target: Azure Ubuntu VPS running the FastAPI backend behind Nginx.

## One-Time Server Setup

SSH into the VPS, then install Git if needed:

```bash
sudo apt-get update
sudo apt-get install -y git
```

Clone the backend repository:

```bash
sudo mkdir -p /opt/qcm-extractor-api
sudo chown "$USER:$USER" /opt/qcm-extractor-api
git clone https://github.com/ayoubi8/qcm-extrqctor-v2.git /opt/qcm-extractor-api/current
cd /opt/qcm-extractor-api/current
```

Install service files and Python dependencies:

```bash
sudo bash infra/vps/deploy_ubuntu.sh
```

Edit the environment file:

```bash
sudo nano /etc/qcm-extractor-api.env
```

Required values:

```env
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENROUTER_API_KEY=...
QCM_APP_ENV=production
QCM_DEPLOY_TARGET=vps-api
QCM_CORS_ALLOW_ORIGINS=https://your-frontend.vercel.app
QCM_MAX_SOURCE_FILE_BYTES=52428800
QCM_LOG_LEVEL=INFO
PORT=8000
```

Start the API:

```bash
sudo systemctl restart qcm-extractor-api
sudo systemctl status qcm-extractor-api
curl http://127.0.0.1:8000/health
```

## Nginx Reverse Proxy

Copy the template and edit `server_name`:

```bash
sudo cp infra/vps/nginx.qcm-extractor-api.conf /etc/nginx/sites-available/qcm-extractor-api
sudo nano /etc/nginx/sites-available/qcm-extractor-api
sudo ln -sf /etc/nginx/sites-available/qcm-extractor-api /etc/nginx/sites-enabled/qcm-extractor-api
sudo nginx -t
sudo systemctl reload nginx
```

If you do not have a domain yet, use the free `sslip.io` hostname that maps to the VPS IP:

```text
20.5.176.133.sslip.io
```

Set `server_name` in `/etc/nginx/sites-available/qcm-extractor-api` to:

```nginx
server_name 20.5.176.133.sslip.io;
```

Then use Certbot for HTTPS:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 20.5.176.133.sslip.io
```

After HTTPS is active, test:

```bash
curl https://20.5.176.133.sslip.io/health
```

## Azure Network Rules

Open inbound ports:

- `22` for SSH.
- `80` for HTTP.
- `443` for HTTPS after Certbot.

Do not expose port `8000` publicly; it should stay bound to `127.0.0.1`.

## Update Deployment

```bash
cd /opt/qcm-extractor-api/current
sudo -u qcm git pull origin main
sudo bash infra/vps/deploy_ubuntu.sh
sudo systemctl restart qcm-extractor-api
curl http://127.0.0.1:8000/health
```

## Frontend Wiring

Set the frontend Vercel variable to the public API URL:

```env
VITE_API_BASE_URL=https://api.your-domain.com
```

Then redeploy the frontend.

Without a custom domain, use:

```env
VITE_API_BASE_URL=https://20.5.176.133.sslip.io
```
