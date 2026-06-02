# Network-Reachable MediaMTX Install Design

Date: 2026-06-02
Status: Proposed

## Product Goal

An installed OmniSight master must work when operators and edge devices reach it
through a dedicated private IP or DNS name instead of `localhost`. A MacBook
master installed with `--public-url http://MASTER_IP:3000` should not ship any
browser-facing MediaMTX configuration that only trusts or advertises loopback
addresses.

The operator promise is:

1. If the installer is given a reachable master URL, browser login, API calls,
   Live streams, and WebRTC negotiation use that same reachable host.
2. Loopback remains available for local troubleshooting.
3. Private infrastructure services stay bound to loopback unless the product
   explicitly needs them on the LAN.

## Current State

The master installers correctly derive most public-facing URLs from
`--public-url`:

- frontend URL
- API base URL
- OIDC authority
- Keycloak public URL
- Keycloak bind address for non-loopback hosts
- backend CORS origins

The remaining risk is MediaMTX. Both master installers copy
`infra/mediamtx/mediamtx.yml` unchanged into `/etc/vezor/mediamtx/mediamtx.yml`.
That source file currently includes only loopback browser origins and loopback
WebRTC advertised hosts:

- `apiAllowOrigins`
- `webrtcAllowOrigins`
- `hlsAllowOrigins`
- `webrtcAdditionalHosts`

When a remote browser reaches the master at `http://MASTER_IP:3000`, MediaMTX can
still reject direct browser-origin requests or advertise `127.0.0.1` candidates
for WebRTC. Standard HLS and MJPEG traffic is mostly proxied through the backend,
but forced WebRTC and any future direct MediaMTX browser path can break.

## Scope

In scope:

- Render installed MediaMTX config from installer inputs instead of copying the
  development config unchanged.
- Update macOS and Linux master installers.
- Update Linux edge installer so edge MediaMTX also trusts the master frontend
  origin and advertises the edge stream host.
- Preserve loopback origins and hosts for local troubleshooting.
- Add installer tests for rendered origins, WebRTC hosts, and JWKS URL rewrite.
- Update the MacBook/Jetson reinstall guide with verification steps.

Out of scope:

- Exposing Postgres, Redis, MinIO, normal NATS, MediaMTX API, or worker metrics
  to the LAN.
- Changing the development Docker Compose defaults.
- Kubernetes or Helm MediaMTX behavior.
- Replacing MediaMTX transport selection or Live player logic.

## Product Rules

### 1. Public Installer Input Drives Browser-Facing Config

For master installs, `--public-url` is the source of truth for:

- frontend origin allowed by MediaMTX
- WebRTC additional host advertised by MediaMTX
- documentation and smoke-test expectations

For edge installs, `--api-url` identifies the master API and the installer derives
the default master frontend origin from the same host with port `3000`. An
optional explicit frontend URL may override that derived origin for nonstandard
deployments.

### 2. Loopback Is Allowed, Not Exclusive

Installed MediaMTX config should include both:

- the reachable public origin/host from installer input
- `http://localhost:3000`, `http://127.0.0.1:3000`, `localhost`, and `127.0.0.1`

Duplicate entries must be removed while preserving stable order.

### 3. Private Services Stay Private

The following loopback binds are intentional and should not be treated as bugs:

- master Postgres, Redis, normal NATS, NATS monitoring, MinIO, MinIO console
- MediaMTX API
- edge MediaMTX API
- worker metrics
- health checks inside containers

The product only needs frontend, backend API, Keycloak when public login is
enabled, NATS leaf, and MediaMTX stream ports to be reachable on the relevant
network.

### 4. Installed Config Must Be Inspectable

After install, an operator should be able to inspect
`/etc/vezor/mediamtx/mediamtx.yml` and confirm:

- `apiAllowOrigins`, `webrtcAllowOrigins`, and `hlsAllowOrigins` include the
  master frontend origin.
- `webrtcAdditionalHosts` includes the master or edge private IP/DNS name.
- edge `authJWTJWKS` points at the master API, not the Docker-internal backend
  hostname.

## Proposed Design

### Shared Renderer

Add a small installer helper:

`installer/lib/render_mediamtx_config.py`

The helper should use only the Python standard library because installers run on
fresh macOS/Linux hosts where PyYAML may not exist. It should perform a bounded,
tested rewrite of known top-level MediaMTX keys:

- `authJWTJWKS`
- `apiAllowOrigins`
- `webrtcAllowOrigins`
- `hlsAllowOrigins`
- `webrtcAdditionalHosts`

Inputs:

- `--source PATH`
- `--dest PATH`
- `--frontend-origin ORIGIN` repeatable
- `--webrtc-host HOST` repeatable
- `--jwks-url URL` optional

Behavior:

- normalize origins by stripping trailing slashes
- ignore empty values
- de-duplicate while preserving first occurrence
- replace only the known list blocks and optional JWKS line
- write atomically to the destination
- fail loudly if a required key is missing from the source template

### Master Installers

Replace the raw MediaMTX config copy in both:

- `installer/macos/install-master.sh`
- `installer/linux/install-master.sh`

The installer should pass:

- `--frontend-origin "$PUBLIC_URL"`
- `--frontend-origin "http://localhost:3000"`
- `--frontend-origin "http://127.0.0.1:3000"`
- `--webrtc-host "$PUBLIC_HOST"`
- `--webrtc-host "localhost"`
- `--webrtc-host "127.0.0.1"`

`PUBLIC_HOST` should be parsed from `PUBLIC_URL` using the installer’s existing
URL host helper, without the port.

### Edge Installer

Replace the inline JWKS rewrite in:

- `installer/linux/install-edge.sh`

The edge installer should pass:

- `--jwks-url "$API_URL/.well-known/argus/mediamtx/jwks.json"`
- `--frontend-origin "$MASTER_FRONTEND_URL"`
- `--frontend-origin "http://localhost:3000"`
- `--frontend-origin "http://127.0.0.1:3000"`
- `--webrtc-host "$EDGE_STREAM_HOST"`
- `--webrtc-host "localhost"`
- `--webrtc-host "127.0.0.1"`

`MASTER_FRONTEND_URL` should default to the `--api-url` scheme and host with port
`3000`, with a CLI override for custom frontend ports. `EDGE_STREAM_HOST` should
be parsed from `--public-mediamtx-rtsp-url`.

## UX And Documentation

Update the MacBook/Jetson reinstall guide with:

- a short explanation that loopback binds for private services are expected
- a warning that `--public-url http://127.0.0.1:3000` is only valid for a local
  browser
- a post-install MediaMTX config check for origins and WebRTC hosts
- a forced WebRTC Live smoke step when testing from another machine on the LAN

The guide should make the dedicated-IP path explicit:

```bash
sudo ./installer/macos/install-master.sh \
  --public-url "http://MASTER_PRIVATE_IP:3000"
```

## Acceptance Criteria

- A macOS master install with `--public-url http://192.168.1.25:3000` writes a
  MediaMTX config containing `http://192.168.1.25:3000` in every browser-origin
  allow list.
- The same config includes `192.168.1.25` in `webrtcAdditionalHosts`.
- Linux master install behavior matches macOS.
- Edge install renders `authJWTJWKS` from `--api-url`.
- Edge install includes the derived or explicit master frontend origin in every
  browser-origin allow list.
- Edge install includes the host from `--public-mediamtx-rtsp-url` in
  `webrtcAdditionalHosts`.
- Installer tests fail if the raw development MediaMTX config is copied
  unchanged into installed config.
- Documentation distinguishes harmful loopback browser-facing config from safe
  loopback service binds.

## Recommended Execution Mode

Use one sequential implementation path rather than multi-agent execution. The
change is small but tightly coupled: one renderer, three installer call sites,
one test cluster, and one documentation update. Parallel agents would add more
coordination cost than useful speed for this fix.
