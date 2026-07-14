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
sudo systemctl restart qcm-extractor-worker
curl http://127.0.0.1:8000/health
```

## Worker Service (durable task executor)

The worker dequeues tasks from the same Supabase queue as the API and runs Step 1-4,
Manual Auto Run, and AI Auto Run handlers. It must run as a supervised long-running
process alongside the API.

Create `/etc/systemd/system/qcm-extractor-worker.service`:

```ini
[Unit]
Description=QCM Extractor Worker
After=network-online.target qcm-extractor-api.service
Wants=network-online.target

[Service]
Type=simple
User=qcm
WorkingDirectory=/opt/qcm-extractor-api/current
EnvironmentFile=/etc/qcm-extractor-api.env
ExecStart=/opt/qcm-extractor-api/current/.venv/bin/python -m qcm_worker.main
Restart=always
RestartSec=5
StandardOutput=append:/var/log/qcm-extractor/worker.log
StandardError=append:/var/log/qcm-extractor/worker.log

[Install]
WantedBy=multi-user.target
```

`/etc/qcm-extractor-api.env` must include at least:

```env
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
QCM_WORKER_ID=azure-worker-1
QCM_LOG_LEVEL=INFO
```

Enable and start:

```bash
sudo mkdir -p /var/log/qcm-extractor
sudo chown qcm:qcm /var/log/qcm-extractor
sudo systemctl daemon-reload
sudo systemctl enable --now qcm-extractor-worker
sudo systemctl status qcm-extractor-worker
sudo tail -f /var/log/qcm-extractor/worker.log
```

## Database Migrations (Supabase)

Apply migrations `0001`-`0004` in the Supabase Dashboard SQL editor (they are idempotent).
Phase B additionally requires `0005_task_kind_aliases.sql` (adds `step2_orchestrate`,
`manual_autorun`, `ai_autorun` to the `public.task_kind` enum) so Step 2 / Auto Run tasks
can be persisted. Run each `migrations/*.sql` file's contents in the Supabase SQL editor.

```sql
alter type public.task_kind add value if not exists 'step2_orchestrate';
alter type public.task_kind add value if not exists 'manual_autorun';
alter type public.task_kind add value if not exists 'ai_autorun';
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
