#!/bin/bash
set -eux

dnf update -y
dnf install -y postgresql15-server postgresql15

/usr/bin/postgresql-setup --initdb

sed -i "s/^#listen_addresses =.*/listen_addresses = '*'/" /var/lib/pgsql/data/postgresql.conf

cat >> /var/lib/pgsql/data/pg_hba.conf <<EOF
host    all             all             ${app_cidr}      md5
host    all             all             ${lambda_cidr}   md5
EOF

systemctl enable postgresql
systemctl start postgresql

sudo -u postgres psql <<SQL
CREATE USER ${db_username} WITH PASSWORD '${db_password}';
CREATE DATABASE ${db_name} OWNER ${db_username};
GRANT ALL PRIVILEGES ON DATABASE ${db_name} TO ${db_username};
SQL