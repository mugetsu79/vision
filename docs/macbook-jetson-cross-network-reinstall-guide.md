# MacBook Master And Jetson Edge Cross-Network Reinstall Guide

Use this when rerunning the installer after the MacBook master and Jetson edge
are no longer on the same LAN, for example when one side is reachable through a
VPN, routed subnet, tunnel, or port-forwarded address.

Command sources:

- `docs/product-installer-and-first-run-guide.md`
- `installer/macos/install-master.sh --help`
- `installer/linux/install-edge.sh --help`
- `archive/macbook-pro-jetson-portable-demo-install-guide.md` for older network
  port notes only

## 0. Reboot-Only Fast Path

Use this section when the MacBook and Jetson were already installed and paired,
and the only event was a shutdown or reboot. If the reachable MacBook and
Jetson addresses did not change, do not rerun the installers and do not set the
variables in section 1.

On the MacBook:

```bash
cd /opt/vezor/current
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
docker ps --filter name=vezor-master
```

If `docker ps` cannot reach Docker, start Docker Desktop and rerun the checks
after the Docker engine is ready.

On the Jetson:

```bash
systemctl status vezor-edge.service
/opt/vezor/current/bin/vezorctl status --json
docker ps --filter name=vezor
docker logs --tail 80 vezor-supervisor
```

Then open the normal master frontend URL in the browser. If Control ->
Deployment shows fresh master and Jetson heartbeats, the Jetson credential is
active, and Live telemetry/video work, stop here.

Continue to the reinstall steps below only when one of these changed:

- the MacBook address that the Jetson or browser must reach
- the Jetson stream address that the MacBook or browser must reach
- the branch needs to be updated before validation
- the installed services are still stale after normal service restart checks
- the Jetson needs to be re-paired or its credential is no longer active

## 1. Pick The Reachable Addresses

Do not use `127.0.0.1`, `localhost`, or a private LAN address unless that exact
address is reachable from the other node.

Fill these in first:

```bash
MASTER_PUBLIC_HOST="MASTER_VPN_IP_OR_DNS_REACHABLE_BY_BROWSER_AND_JETSON"
JETSON_STREAM_HOST="JETSON_VPN_IP_OR_DNS_REACHABLE_BY_MASTER"

MASTER_PUBLIC_URL="http://${MASTER_PUBLIC_HOST}:3000"
MASTER_API_URL="http://${MASTER_PUBLIC_HOST}:8000"
MASTER_KEYCLOAK_URL="http://${MASTER_PUBLIC_HOST}:8080"
```

Set the relevant variables in each shell where you run commands; the MacBook
and Jetson shells do not share environment variables.

Required reachability:

| Direction | Required target |
|---|---|
| Operator browser -> MacBook | `http://$MASTER_PUBLIC_HOST:3000` |
| Operator browser -> MacBook | `http://$MASTER_PUBLIC_HOST:8080` for Keycloak auth |
| Jetson -> MacBook | `http://$MASTER_PUBLIC_HOST:8000/healthz` |
| Jetson -> MacBook | `nats://$MASTER_PUBLIC_HOST:7422` |
| MacBook -> Jetson | `rtsp://$JETSON_STREAM_HOST:8554` |
| Browser -> master MediaMTX | UDP `8189` must work for WebRTC browser delivery |

If the Jetson RTSP service is exposed on a non-standard public port, use the
full edge installer option:

```bash
PUBLIC_MEDIAMTX_RTSP_URL="rtsp://JETSON_PUBLIC_HOST_OR_IP:PUBLIC_RTSP_PORT"
```

and pass `--public-mediamtx-rtsp-url "$PUBLIC_MEDIAMTX_RTSP_URL"` to the edge
installer.

## 2. Update The Branch On Both Hosts

MacBook:

```bash
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
```

Jetson:

```bash
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-installer
git pull --ff-only origin codex/omnisight-installer
```

## 3. Rerun The MacBook Master Installer

Run this on the MacBook. The `--public-url` host is important: the macOS
installer derives the public frontend, API, and Keycloak URLs from it.

```bash
cd /opt/vezor/current

sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "$MASTER_PUBLIC_URL" \
  --data-dir /var/lib/vezor
```

Validate from the MacBook:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS "$MASTER_API_URL/healthz"
curl -fsS "$MASTER_KEYCLOAK_URL/realms/argus-dev/.well-known/openid-configuration"
docker ps --filter name=vezor-master
```

When `$MASTER_PUBLIC_HOST` is not `localhost` or `127.0.0.1`, the Keycloak
container should show `0.0.0.0:8080->8080/tcp` in `docker ps`. If it still
shows `127.0.0.1:8080->8080/tcp`, browser sign-in cannot reach Keycloak from
the remote address; rerun the master installer from the updated branch.
After backend startup, the existing Keycloak frontend client is also reconciled
to the current `$MASTER_PUBLIC_URL`, and the backend allows that frontend URL
through CORS. This matters after IP changes because first-run may already be
complete and the original Keycloak client may still contain only localhost
redirect URIs.

Validate from the Jetson:

```bash
curl -fsS "$MASTER_API_URL/healthz"
```

For a first install, open:

```text
http://MASTER_VPN_IP_OR_DNS_REACHABLE_BY_BROWSER_AND_JETSON:3000/first-run
```

and generate a fresh bootstrap token on the MacBook:

```bash
/opt/vezor/current/bin/vezorctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Use the returned `vzboot_...` token only in `/first-run`.

## 4. Rerun The Jetson Edge Installer

The dev manifest still requires the Jetson Python 3.10 ONNX Runtime GPU wheel:

```bash
JETSON_ORT_WHEEL_URL="https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.23.0-cp310-cp310-linux_aarch64.whl"
```

### Existing Paired Jetson After A Network Change

Use this when the Jetson was already paired successfully before. This preserves
the existing credential and updates the master API URL, NATS leaf URL, JWKS URL,
and public Jetson stream host.

```bash
cd /opt/vezor/current

sudo ./installer/linux/install-edge.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --unpaired \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-stream-host "$JETSON_STREAM_HOST" \
  --jetson-ort-wheel-url "$JETSON_ORT_WHEEL_URL"
```

If the Jetson stream uses a forwarded RTSP port, use this variant:

```bash
sudo ./installer/linux/install-edge.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --unpaired \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-mediamtx-rtsp-url "$PUBLIC_MEDIAMTX_RTSP_URL" \
  --jetson-ort-wheel-url "$JETSON_ORT_WHEEL_URL"
```

Only use `--unpaired` after one successful paired install has written
`edge_node_id` into `/etc/vezor/supervisor.json`. If the installer refuses the
unpaired update, create a fresh Pair Jetson edge session and use the paired
install command below.

### Fresh Or Re-Paired Jetson

In the master UI, open Control -> Deployment, click Pair Jetson edge, and copy
both values:

- `Session ID`
- `Pairing code`

Then run this on the Jetson:

```bash
cd /opt/vezor/current

sudo ./installer/linux/install-edge.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --api-url "$MASTER_API_URL" \
  --session-id "PAIRING_SESSION_ID" \
  --pairing-code "PAIRING_CODE" \
  --edge-name "jetson-portable-1" \
  --model-dir /var/lib/vezor/models \
  --public-stream-host "$JETSON_STREAM_HOST" \
  --jetson-ort-wheel-url "$JETSON_ORT_WHEEL_URL"
```

## 5. Validate

On the Jetson:

```bash
systemctl status vezor-edge.service
/opt/vezor/current/bin/vezorctl status --json
docker ps --filter name=vezor
docker logs --tail 80 vezor-edge-nats-leaf
docker logs --tail 120 vezor-supervisor
curl -fsS http://127.0.0.1:9997/v3/paths/list
```

On the MacBook:

```bash
curl -fsS "$MASTER_API_URL/healthz"
docker ps --filter name=vezor-master
```

From the MacBook or any host that can reach the Jetson stream address:

```bash
ffprobe -v error "rtsp://${JETSON_STREAM_HOST}:8554/cameras/CAMERA_ID/passthrough"
```

In the UI:

- Control -> Deployment shows fresh master and Jetson heartbeats.
- Jetson credential status is active.
- Jetson service manager is `systemd`.
- The Jetson camera is assigned to the Jetson edge node.
- Live shows telemetry and video through the master frontend URL for this
  network, not a stale URL from a previous network.

## 6. Common Mistakes

- `--public-url "http://127.0.0.1:3000"` on the MacBook when the browser or
  Jetson is remote. Use `$MASTER_PUBLIC_URL`.
- `--api-url "http://127.0.0.1:8000"` on the Jetson. Use `$MASTER_API_URL`.
- Seeing the master frontend but no Keycloak sign-in redirect. Confirm
  `$MASTER_KEYCLOAK_URL/realms/argus-dev/.well-known/openid-configuration`
  is reachable from the operator browser network and that `docker ps` exposes
  Keycloak on `0.0.0.0:8080` for non-loopback public URLs.
- Seeing Keycloak metadata work but the Sign in button still does nothing.
  Reinstall from the updated branch so backend startup repairs the existing
  Keycloak `argus-frontend` redirect URIs and web origins for
  `$MASTER_PUBLIC_URL`.
- Omitting `--public-stream-host` after the Jetson changes networks. The
  master will keep trying to read the old Jetson RTSP address.
- Using only the short pairing code. The edge installer needs both
  `--session-id` and `--pairing-code`.
- Pointing edge workers at `nats://127.0.0.1:4222`. Installed workers must use
  the local leaf at `nats://nats-leaf:4222`; the installer writes this.
