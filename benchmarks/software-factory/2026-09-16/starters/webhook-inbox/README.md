# Webhook inbox starter

This deliberately incomplete starter runs on Python 3.11+ with no installed packages. Read `prompt.md` for the exact acceptance contract and `AGENTS.md` for the project release policy.

Start locally:

```console
python inbox.py --db inbox.sqlite3 --config config.example.json --host 127.0.0.1 --port 8080
```

The startup line is JSON containing the actual host and port. `GET /health` works; ingestion, authorization, durable storage, and pagination are left to implement. Example credentials are fixtures, not production credentials.

Run the public checks:

```console
python -m unittest -v test_smoke
```

The health test passes in the starter. The round-trip test intentionally fails until the product is implemented. Add broader tests and complete the operating and release documentation as part of the assignment.
