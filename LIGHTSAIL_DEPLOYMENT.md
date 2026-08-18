# AWS Lightsail USD 12 single-instance deployment

ArthNivo runs entirely on one Lightsail Ubuntu instance. The application,
PostgreSQL, Redis, and Caddy are separate Docker containers, but there is only
one AWS compute resource and one USD 12/month instance charge.

```text
Internet
   |
   v
Caddy :80/:443
   |
   v
ArthNivo React + FastAPI
   |                 |
   v                 v
PostgreSQL         Redis
persistent volume  persistent volume
```

PostgreSQL and Redis are not exposed through the instance firewall or Docker
host ports. Only Caddy can reach ArthNivo, and only ArthNivo can reach the
private data network.

## Cost and limitations

The selected Lightsail Linux bundle currently costs USD 12/month and provides
2 GB RAM, 2 vCPUs, 60 GB SSD storage, and its data-transfer allowance. The
provisioning helper discovers the currently active bundle matching USD 12
instead of hard-coding its AWS bundle ID.

There is no separate managed PostgreSQL or Redis charge. Optional instance
snapshots, domain registration, AI-provider usage, and transfer overages are
separate.

This arrangement is appropriate for an interview demonstration or small
private deployment. It is one failure and scaling domain: restarting or losing
the instance affects the API, PostgreSQL, and Redis together. Use managed data
services or separate instances before treating it as highly available
production infrastructure.

## Step 0: rotate the exposed Groq key

Revoke every Groq key that has appeared in chat, screenshots, logs, or Git
history. Generate a new key. Never paste the replacement or AWS credentials
into chat.

Confirm secrets are not tracked or sent to Docker:

```bash
git ls-files .env lightsail.env .lightsail
git check-ignore lightsail.env .lightsail
```

The first command must print nothing. The second must report both paths as
ignored.

## Step 1: configure non-root AWS access

Enable MFA and billing alerts. Use a non-root administrator or deployment role.
The root account must not be used for routine deployment.

```bash
aws login --profile arthnivo-deploy --region ap-south-1
aws sts get-caller-identity --profile arthnivo-deploy
```

If the organization uses IAM Identity Center, configure the named profile with
`aws configure sso` instead. The identity needs permissions to create and
manage Lightsail instances, key pairs, static IPs, tags, and firewall rules.

Required local tools are already installed on the development Mac:

- AWS CLI version 2;
- Docker Desktop;
- SSH, SCP, and rsync.

## Step 2: create the USD 12 instance

Find the public IPv4 address of the development network and express it as a
single-address CIDR, for example `203.0.113.10/32`. This limits SSH access to
that address. HTTP and HTTPS remain public.

Create the latest active Ubuntu instance, an SSH key, an attached static IP,
and firewall rules:

```bash
.venv/bin/python -m scripts.provision_lightsail_instance \
  --profile arthnivo-deploy \
  --region ap-south-1 \
  --availability-zone ap-south-1a \
  --instance arthnivo \
  --ssh-cidr YOUR_PUBLIC_IP/32 \
  --confirm-monthly-charge USD12
```

The command saves the new private SSH key under the ignored `.lightsail`
directory with mode 600. It installs Docker, Docker Compose, and rsync through
cloud-init and prints the attached static IP. Do not delete or detach the
static IP while the instance is active.

## Step 3: prepare PostgreSQL and Redis credentials

Copy the template if `lightsail.env` does not already exist:

```bash
cp lightsail.env.example lightsail.env
chmod 600 lightsail.env
```

Put only the newly rotated `GROQ_API_KEY` into this file. Do not add external
PostgreSQL or Redis URLs.

For the first IP-based deployment, replace `INSTANCE_STATIC_IP` below:

```bash
.venv/bin/python -m scripts.prepare_lightsail_instance_env \
  --host INSTANCE_STATIC_IP \
  --env-file lightsail.env
```

The helper generates strong PostgreSQL and Redis passwords without printing
them. It configures Caddy for HTTP until a domain is available. Do not enter
financial data or passwords over public HTTP; use this mode only for the first
connectivity check, then complete the HTTPS step before demonstrating login.

## Step 4: deploy the full stack

Replace `INSTANCE_STATIC_IP` with the value printed during provisioning:

```bash
.venv/bin/python -m scripts.deploy_lightsail_instance \
  --host INSTANCE_STATIC_IP \
  --key .lightsail/arthnivo-deploy.pem \
  --env-file lightsail.env
```

The deployment helper:

1. waits for cloud-init and Docker;
2. uploads source without `.env`, `lightsail.env`, databases, or local caches;
3. separately uploads `lightsail.env` with mode 600;
4. builds the React and FastAPI production image on the instance;
5. starts PostgreSQL, Redis, ArthNivo, and Caddy;
6. waits for healthy dependencies;
7. verifies `/health`, `/ready`, and `/version`.

PostgreSQL data is stored in the `arthnivo_postgres-data` Docker volume. Redis
uses `arthnivo_redis-data`, application backups use
`arthnivo_finance-backups`, and Caddy certificate data has its own volumes.
Restarting containers or rebooting the instance does not remove these volumes.

## Step 5: enable HTTPS before using login

Point a domain or subdomain A record to the instance static IP. After DNS
resolves, configure that exact hostname:

```bash
.venv/bin/python -m scripts.prepare_lightsail_instance_env \
  --host app.example.com \
  --https \
  --env-file lightsail.env

.venv/bin/python -m scripts.deploy_lightsail_instance \
  --host INSTANCE_STATIC_IP \
  --key .lightsail/arthnivo-deploy.pem \
  --env-file lightsail.env \
  --public-url https://app.example.com
```

Caddy obtains and renews the public TLS certificate automatically. Ports 80
and 443 must remain open for certificate issuance and HTTPS traffic.

## Step 6: verify and create demonstration data

```bash
export ARTHNIVO_URL=https://app.example.com
curl --fail "$ARTHNIVO_URL/health"
curl --fail "$ARTHNIVO_URL/ready"
curl --fail "$ARTHNIVO_URL/version"
```

Open the HTTPS URL and register a profile using fictional interview data. Test
login, transaction creation, recurring EMI processing, investment tracking,
export, and one AI question.

Inspect the server when needed:

```bash
ssh -i .lightsail/arthnivo-deploy.pem ubuntu@INSTANCE_STATIC_IP
cd /opt/arthnivo
docker compose --env-file lightsail.env -f compose.lightsail.yaml ps
docker compose --env-file lightsail.env -f compose.lightsail.yaml logs --tail 200
```

## Updates, backups, and recovery

Commit and test every update, then rerun the deployment command. Docker Compose
rebuilds the application while preserving PostgreSQL and Redis volumes.

Create an application-level backup:

```bash
docker compose --env-file lightsail.env -f compose.lightsail.yaml \
  exec arthnivo python -m scripts.backup_data
```

Copy verified backups off the instance and enable automatic Lightsail instance
snapshots. A Docker volume on the same disk is not an off-site backup. Perform
restore drills before relying on the deployment for irreplaceable information.

## Stop all charges

Snapshot or export anything required, then delete the instance. Also release
the static IP after the instance is deleted; an unattached static IP can incur
a charge. Instance deletion permanently removes local PostgreSQL, Redis, Caddy,
and backup volumes unless preserved in a snapshot or external backup.
