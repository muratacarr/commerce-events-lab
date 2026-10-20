#!/bin/sh
# Runs once on an empty data directory. Creates one database per service with a separate
# migration owner and a runtime role that may only connect. Table privileges for the runtime
# role are granted by each service's migrations (PROJECT-016), not here.
set -eu

for svc in order payment inventory; do
  # Values travel through the environment of this one psql process, never through its
  # command-line arguments, so they do not show up in the process list.
  SVC="$svc" \
  OWNER_PW=$(cat "/run/secrets/${svc}_db_owner_password") \
  APP_PW=$(cat "/run/secrets/${svc}_db_app_password") \
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\getenv svc SVC
\getenv owner_pw OWNER_PW
\getenv app_pw APP_PW
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'svc' || '_owner', :'owner_pw') \gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'svc' || '_app', :'app_pw') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', :'svc', :'svc' || '_owner') \gexec
SELECT format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', :'svc') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'svc', :'svc' || '_app') \gexec
SQL
done
