# Host nginx config has moved

The host-level nginx vhost for `vocab.n2deep.co` now lives in the **`n2deep-infra`** repo
(`~/Projects/n2deep-infra`), together with the vhosts for the other two apps sharing the
Lightsail box.

```bash
cd ~/Projects/n2deep-infra
bin/check-drift.sh          # does the box match the repo?
bin/sync-nginx.sh           # install, validate, reload, smoke-test
```

- Vhost: `n2deep-infra/nginx/vocab.n2deep.co`
- One-time setup (DNS, TLS): `n2deep-infra/nginx/SITES.md`
- Box operations (TLS renewal, snapshots, logs, danger list): `n2deep-infra/RUNBOOK.md`

**Why it moved:** `nginx -t` is global and `default_server` follows `sites-enabled/` load
order, so a vhost change in one app repo can break or silently alter the other two sites.
Those files have to be validated as a unit.

## Worth knowing

This site does **not** have its own TLS certificate. `vocab.n2deep.co` is a SAN on the
`tracker.n2deep.co` certificate, which is why the vhost references
`/etc/letsencrypt/live/tracker.n2deep.co/`. That is intentional — don't "correct" it to a
`vocab.n2deep.co` path, which doesn't exist.

The nginx sections of [`CLOUD-DEPLOY.md`](../CLOUD-DEPLOY.md) describe the original
one-time setup and are kept for history, but `n2deep-infra` is now the source of truth for
the vhost itself.
