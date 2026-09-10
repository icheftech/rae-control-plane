# Quick start

See [README.md](README.md#local-setup) for the maintained v0.2 setup and available features.

In this prepared workspace:

```sh
docker compose up -d postgres
.venv312/bin/python scripts/run_backend.py
```

In another terminal:

```sh
cd frontend
API_URL=http://127.0.0.1:18000 npm run dev -- --hostname 127.0.0.1 --port 13000
```

Open http://127.0.0.1:13000 and paste the administrator key from `LOCAL_ACCESS.txt`.
