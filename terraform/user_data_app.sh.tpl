#!/bin/bash
set -eux

dnf update -y
dnf install -y python3 python3-pip nginx

mkdir -p /opt/tavern
cd /opt/tavern

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn psycopg2-binary python-dotenv

cat >/opt/tavern/.env <<EOF
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_username}
DB_PASSWORD=${db_password}
FLASK_PORT=${flask_port}
EOF

cat >/opt/tavern/app.py <<'PY'
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "The Tavern dashboard API is running"
PY

cat >/etc/systemd/system/tavern.service <<EOF
[Unit]
Description=Tavern Flask App
After=network.target

[Service]
WorkingDirectory=/opt/tavern
EnvironmentFile=/opt/tavern/.env
ExecStart=/opt/tavern/venv/bin/gunicorn -w 2 -b 127.0.0.1:${flask_port} app:app
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/nginx/conf.d/tavern.conf <<EOF
server {
    listen 80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:${flask_port};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

systemctl daemon-reload
systemctl enable tavern
systemctl start tavern
systemctl enable nginx
systemctl restart nginx