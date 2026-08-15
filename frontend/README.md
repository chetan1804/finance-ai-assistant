# Khata React frontend

React 19, TypeScript, and Vite power the next-level dashboard. During local
development, Vite proxies `/api` and `/health` to FastAPI at
`http://127.0.0.1:8000`.

```bash
npm install
npm run dev
```

Quality checks:

```bash
npm run lint
npm test
npm run build
```

The production output is written to `dist/`. Docker builds this directory and
sets `FINANCE_UI_DIST` so FastAPI serves it at `/`.
