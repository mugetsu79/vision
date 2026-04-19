# Argus Runbook

See also:

- [deployment-modes-and-matrix.md](/Users/yann.moren/vision/docs/deployment-modes-and-matrix.md)
- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)

## Secrets With SOPS And Age

Argus stores operational secrets under `/Users/yann.moren/vision/infra/secrets/` as encrypted `*.enc.yaml`, `*.enc.json`, or `*.enc.env` files. The repository is configured for SOPS + age through `/Users/yann.moren/vision/.sops.yaml`.

Before the first production deployment:

1. Generate an age keypair on an operator workstation: `age-keygen -o ~/.config/sops/age/keys.txt`.
2. Replace the bootstrap recipient in `/Users/yann.moren/vision/.sops.yaml` with the real team recipient or recipients.
3. Export `SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt`.
4. Create encrypted secret material with `sops infra/secrets/<name>.enc.yaml`.

Recommended secret sets:

- central platform secrets: database password, MinIO credentials, RTSP encryption key, MediaMTX JWT key
- auth secrets: Keycloak admin bootstrap secret and confidential client secrets
- edge secrets: edge node API keys, NATS credentials, remote bootstrap tokens

## Secret Rotation Procedure

Use this sequence when rotating any production secret set:

1. Generate a fresh age recipient and update `/Users/yann.moren/vision/.sops.yaml`.
2. Re-encrypt every tracked secret file with `sops updatekeys infra/secrets/*.enc.yaml`.
3. Rotate the live runtime secret in the backing service first:
   - Postgres user password
   - MinIO root credentials
   - Keycloak client secrets
   - `ARGUS_RTSP_ENCRYPTION_KEY`
   - MediaMTX JWT signing key
   - edge API keys or NATS credentials
4. Roll the central workloads, verify `/healthz`, `/metrics`, login, and stream authorization.
5. Roll edge workers after central verification succeeds.
6. Revoke the previous secret material and remove the old age private key from operator workstations.

## Jetson Orin Nano Super 8 GB Bootstrap

Before starting the edge stack on Jetson Orin Nano Super 8 GB, enable the 25 W Super mode:

```bash
sudo nvpmodel -m 2 && sudo jetson_clocks
```

Then run the local preflight:

```bash
/Users/yann.moren/vision/scripts/jetson-preflight.sh
```

The preflight checks JetPack 6.2, CUDA 12.6, TensorRT 10.x, NVDEC availability, the expected lack of NVENC on Orin Nano, Docker, and `nvidia-container-toolkit`.

## Edge Bring-Up

For a single-node edge deployment:

1. Place the edge model weights under `/Users/yann.moren/vision/models/`.
2. Export the required HQ bootstrap values:
   - `ARGUS_API_BASE_URL`
   - `ARGUS_EDGE_CAMERA_ID`
   - `ARGUS_NATS_URL` if the default leaf upstream does not match your HQ
3. Start the stack with `docker compose -f /Users/yann.moren/vision/infra/docker-compose.edge.yml up -d`.
4. Confirm MediaMTX, OTEL Collector, and the worker metrics endpoint are reachable.

## Authentication Alternative

Keycloak is the default IdP. If an operator standardizes on Authentik instead, keep the same OIDC contract at the SPA and API layers, update the issuer and JWKS configuration, and record the deployment-specific divergence in a new ADR before rollout.
