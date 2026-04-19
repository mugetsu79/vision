# Encrypted Secrets

Store Argus runtime secrets in this directory as SOPS-encrypted files:

- `central.enc.yaml`
- `edge.enc.yaml`
- `keycloak.enc.yaml`

Use age recipients defined in `/Users/yann.moren/vision/.sops.yaml`, then edit with:

```bash
sops infra/secrets/central.enc.yaml
```

Do not commit decrypted variants. The repository `.gitignore` already excludes `*.dec.*` files in this directory.
