#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/app-bootstrap.log | logger -t user-data -s 2>/dev/console) 2>&1

dnf update -y
dnf install -y \
  python3 python3-pip python3-devel \
  git nginx gcc postgresql-devel postgresql15 \
  certbot python3-certbot-nginx amazon-ssm-agent

systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

mkdir -p /opt/tavern
cd /opt/tavern

if [ -d /opt/tavern/repo ]; then
  rm -rf /opt/tavern/repo
fi

git clone https://github.com/CodeTechBen/westmarch_pipeline.git repo

cd /opt/tavern/repo/tavern-dashboard

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip

if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    pip install flask gunicorn psycopg2-binary python-dotenv
fi

cat > /opt/tavern/repo/tavern-dashboard/.env <<EOF
DB_HOST=${db_host}
DB_NAME=${db_name}
DB_USER=${db_username}
DB_PASSWORD=${db_password}
FLASK_PORT=${flask_port}
EOF

until PGPASSWORD='${db_password}' psql -h ${db_host} -U ${db_username} -d ${db_name} -c '\q'; do
  echo "Waiting for database..."
  sleep 5
done

cat >/etc/systemd/system/tavern.service <<EOF
[Unit]
Description=Tavern Flask App
After=network.target

[Service]
WorkingDirectory=/opt/tavern/repo/tavern-dashboard
EnvironmentFile=/opt/tavern/repo/tavern-dashboard/.env
ExecStart=/opt/tavern/repo/tavern-dashboard/venv/bin/gunicorn -w 2 -b 127.0.0.1:${flask_port} app:app
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/nginx/conf.d/tavern.conf <<EOF
server {
    listen 80;
    server_name ${domain_name} www.${domain_name};

    location / {
        proxy_pass http://127.0.0.1:${flask_port};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

rm -f /etc/nginx/conf.d/default.conf || true

systemctl daemon-reload
systemctl enable tavern
systemctl restart tavern
systemctl enable nginx
systemctl restart nginx

cat >/usr/local/bin/bootstrap-cert.sh <<EOF
#!/bin/bash
set -eux

DOMAIN="${domain_name}"
WWW_DOMAIN="www.${domain_name}"
EMAIL="${admin_email}"

PUBLIC_IP=\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

for i in {1..30}; do
  DOMAIN_IP=\$(getent ahostsv4 "\$DOMAIN" | awk '/STREAM/ {print \$1; exit}' || true)
  WWW_IP=\$(getent ahostsv4 "\$WWW_DOMAIN" | awk '/STREAM/ {print \$1; exit}' || true)

  if [ "\$DOMAIN_IP" = "\$PUBLIC_IP" ] && [ "\$WWW_IP" = "\$PUBLIC_IP" ]; then
    certbot --nginx \
      -d "\$DOMAIN" \
      -d "\$WWW_DOMAIN" \
      --non-interactive \
      --agree-tos \
      --email "\$EMAIL" \
      --redirect
    exit 0
  fi

  sleep 20
done

exit 0
EOF

chmod +x /usr/local/bin/bootstrap-cert.sh

cat >/etc/systemd/system/tavern-cert-bootstrap.service <<EOF
[Unit]
Description=Bootstrap Let's Encrypt certificate for Tavern
After=network-online.target nginx.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/bootstrap-cert.sh

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/tavern-cert-renew.service <<EOF
[Unit]
Description=Renew Let's Encrypt certificates

[Service]
Type=oneshot
ExecStart=/usr/bin/certbot renew --quiet
EOF

cat >/etc/systemd/system/tavern-cert-renew.timer <<EOF
[Unit]
Description=Run certbot renew twice daily

[Timer]
OnCalendar=*-*-* 06,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable tavern-cert-bootstrap.service
systemctl start tavern-cert-bootstrap.service || true
systemctl enable tavern-cert-renew.timer
systemctl start tavern-cert-renew.timer