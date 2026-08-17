# Free interview demo deployment

This deployment uses the repository Dockerfile as one Render web service. The
container builds the React frontend and serves it from FastAPI. Neon stores all
finance, authentication, and LangGraph checkpoint data, while Upstash provides
Redis-compatible distributed rate limiting.

This configuration is intended for an interview demonstration or small private
beta. Free services have no production uptime commitment and can sleep, restart,
or reach usage limits.

## Architecture

```text
Browser
   |
   v
Render free web service (React + FastAPI)
   |                         |
   v                         v
Neon PostgreSQL          Upstash Redis
```

The frontend and API share one origin, so `FINANCE_CORS_ORIGINS` is not needed.
The application automatically applies database migrations when the Render
container starts.

## 1. Prepare the repository

Push the project to GitHub only after the verification suite passes. Confirm
that `.env`, local databases, and backups are absent from the commit:

```bash
git status
git ls-files .env data backups
```

The second command should print nothing for secrets or runtime data. Rotate any
provider key that has previously been pasted into chat, logs, or screenshots.

## 2. Create free PostgreSQL on Neon

1. Create a Neon project in a region close to the Render service. The supplied
   Blueprint selects Singapore.
2. Copy the PostgreSQL connection string from Neon.
3. Keep `sslmode=require` in the connection string.
4. Use that value for `FINANCE_DATABASE_URL` in Render.

Do not configure `FINANCE_CHECKPOINT_URL`. When it is absent, checkpoints use
the same PostgreSQL database automatically. The Blueprint sets both connection
pool minimums to zero so an idle database can scale down.

## 3. Create free Redis on Upstash

1. Create an Upstash Redis database near the Render and Neon regions.
2. Copy its TLS connection string, including its password.
3. Confirm that it begins with `rediss://`.
4. Use it for `FINANCE_REDIS_URL` in Render.

The URL is a secret. Do not put it in `.env.example`, `render.yaml`, GitHub, or
an interview screenshot.

## 4. Deploy through the Render Blueprint

1. In Render, choose **New > Blueprint** and connect this GitHub repository.
2. Render reads [`render.yaml`](render.yaml) and builds the root Dockerfile.
3. Keep the service name `arthnivo-demo`, or choose another unique
   name before the first deployment.
4. Supply the four prompted secret values:

   - `GROQ_API_KEY`
   - `FINANCE_DATABASE_URL`
   - `FINANCE_REDIS_URL`
   - `FINANCE_ALLOWED_HOSTS`

`FINANCE_ALLOWED_HOSTS` is the final Render hostname without a scheme or path.
For the default service name it is:

```text
arthnivo-demo.onrender.com
```

If Render requires a different service name, use its exact generated hostname.
For a later custom domain, use a comma-separated value containing both hosts.

The Blueprint uses `/health` for the platform health probe. Unlike `/ready`,
this does not continuously query Neon and Redis, allowing free data services to
idle. Use `/ready` manually to verify dependencies before the interview.

## 5. Verify the live service

Replace the example hostname below:

```bash
export DEMO_BASE_URL=https://arthnivo-demo.onrender.com
curl --fail "$DEMO_BASE_URL/health"
curl --fail "$DEMO_BASE_URL/ready"
curl --fail "$DEMO_BASE_URL/version"
```

Open the root URL, create one demonstration profile, and use only fictional
information. A useful interview dataset includes:

- one salary income and three ordinary expenses;
- one home-loan EMI schedule;
- one mutual-fund SIP investment;
- one category budget and one savings goal;
- one generated notification;
- enough records to ask the AI assistant about spending, an EMI, and investment
  contributions.

Do not publish demo credentials in the repository. Share them privately with an
interviewer or create a fresh profile during the demonstration.

## 6. Interview-day checklist

- Open the live URL at least two minutes before the call so the free web service
  has time to wake.
- Confirm `/ready` reports PostgreSQL, checkpoints, and rate limiting as ready.
- Test login and one AI question.
- Keep screenshots or a short screen recording as a fallback.
- Keep the local Docker version available if the interview network is unstable.

Local fallback:

```bash
docker build -t arthnivo-demo .
docker run --rm --env-file .env -p 8000:8000 arthnivo-demo
```

## Free-tier boundaries

- Render may sleep after inactivity, so the first request can be slow.
- A sleeping Render instance cannot run a dependable background scheduler.
- EMI and investment generation remains manual or dashboard-triggered on this
  free demonstration deployment.
- Monitor Neon, Upstash, and Render usage dashboards.
- Before accepting real customer financial data, move to paid services with
  backups, monitoring, an uptime objective, and a tested recovery process.
