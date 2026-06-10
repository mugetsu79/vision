# Vezor Admin And Operations Guide

Date: 2026-06-10
Version: 2026.1

This guide is for tenant admins, platform superadmins, and operators who own
the installed Vezor environment after first-run.

## Admin Model

Vezor uses tenant-aware RBAC:

- `viewer`: read-only operational visibility.
- `operator`: live operation and routine scene workflows.
- `admin`: tenant-scoped administration.
- `superadmin`: platform-scoped administration in the `platform-admin` realm.

The first tenant admin is created in `/first-run`. The first platform
superadmin is created in `/platform-bootstrap` with a separate one-time local
token. After that, admins and platform superadmins should use the Vezor UI, not
direct Keycloak administration, for normal user management.

## Creating Tenants

Only platform superadmins can create tenants:

1. Sign in with **Platform sign in**.
2. Open **Users**.
3. Enter tenant name and optional slug.
4. Click **Create tenant**.
5. Create at least one tenant admin for the new tenant.

Tenant slugs should be stable because identity and audit paths may refer to
them.

## Creating Users And Admins

Tenant admins:

- can create users only in their own tenant
- can assign `viewer`, `operator`, or `admin`
- can reset temporary passwords for users in their tenant
- cannot create `superadmin`

Platform superadmins:

- can list tenants
- can create tenants
- can create tenant users and tenant admins in any tenant
- can update and reset tenant users across tenants
- cannot create another platform superadmin through the tenant user form

Use temporary passwords only through an approved secret-sharing process. Do not
place passwords in tickets, docs, screenshots, or support bundles.

## Scene Operations

Scene health depends on several independent contracts:

- site exists
- source stream can be reached from the worker node
- model row exists
- target runtime artifact is valid when required
- artifact has been synced to the assigned edge node
- worker is desired and running
- stream rendition can be published and consumed
- rules, privacy, boundaries, and calibration are internally valid

When a scene says **Needs setup** or **Needs attention**, open **Operations**
and focus that scene. Do not treat a green model badge alone as a full scene
pass.

## Worker Lifecycle

Installed operation is supervisor-owned:

- central supervisor owns central workers
- edge supervisor owns edge workers
- UI lifecycle controls desired state and constrained lifecycle requests
- service state and heartbeat come from supervisor reports

Copyable worker commands are development fallback and break-glass tools. They
are not the normal product operating model.

## Model Operations

Use **Models** as the source of truth:

- register source models from Catalog
- import trusted artifacts when needed
- build TensorRT artifacts on the Jetson target
- sync source and runtime artifacts to edge nodes
- inspect model inventory before editing edge scenes

Runtime artifacts are target-specific. A TensorRT engine that is valid on one
Jetson stack is not portable evidence for a different stack.

## Deployment Operations

Use **Deployment** to:

- verify central and edge install health
- pair nodes
- rotate credentials
- unpair retired nodes
- collect redacted support bundles
- inspect service-manager evidence

After rebuilding edge packages, install the packaged service on the Jetson and
record `systemctl status` evidence for both:

```bash
sudo systemctl status vezor-edge.service --no-pager
sudo systemctl status vezor-edge-agent.service --no-pager
```

## Core Link Operations

Use **Links** for site link posture:

- add logical link paths for edge sites
- configure monitoring targets
- run backend synthetic checks for backend-side reachability
- run edge-agent samples for real edge vantage point evidence
- use the master UDP reflector for authenticated UDP sequence loss and latency
- trigger throughput manually when needed

The master is a target-only control-plane site. Operators should not configure
local link paths or throughput checks on the master as if it were an edge site.

## Support Bundles

Support bundles should be the default evidence path for install and runtime
debugging. They are designed to redact common secrets, but operators still need
to review them before sharing outside the trusted team.

Never add the following manually to a support bundle:

- raw camera credentials
- bearer tokens
- node credentials
- bootstrap tokens
- reflector secrets
- sudo passwords
- cloud object-store secrets

## Reset And Rebuild Policy

For a fresh destructive reset:

- document live evidence first
- preserve model files unless the reset specifically includes model deletion
- stop only Vezor-owned services and containers
- do not run global Docker prune
- do not delete unrelated Docker resources
- rebuild from the final committed branch
- rerun first-run, platform bootstrap, pairing, model registration, runtime
  artifact, scene, Link, Evidence, and billing smokes

## Release Gates

Before a pilot release or customer demo, record:

- git branch and commit
- installer manifest
- image references or locally built image hashes
- master service health
- central supervisor evidence
- Jetson supervisor evidence
- edge-agent service evidence
- model inventory
- TensorRT build evidence
- scene readiness
- Live screenshot or smoke evidence
- Evidence/history deterministic fixture or real evidence
- Core Link UDP probe evidence
- billing usage evidence if billing is enabled

Mark each item `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. Missing prerequisites
are not passes.
