# R.A.E. operator console

Next.js and React client for the local FastAPI control plane.

```sh
npm ci
API_URL=http://127.0.0.1:18000 npm run dev -- --hostname 127.0.0.1 --port 13000
```

The server proxies `/api/*` to `API_URL`. Enter a configured API key to connect; the console retains it in memory only. No `NEXT_PUBLIC` secret is required. Entra federation is not yet wired into this build.

Includes workflows, policies, emergency stops, change requests, and audit history. All displayed records come from PostgreSQL. Backend and startup details are in the root README.

Validation: `npm run lint`, `npm run type-check`, `npm run build`.
