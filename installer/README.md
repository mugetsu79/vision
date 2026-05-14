# Vezor Installer

This package contains the product installer support code for the no-console
Vezor first-run path.

The installer tree is intentionally separate from the backend and frontend
development stacks. Its job is to validate release manifests, install local
service artifacts, provide local diagnostics, and support pairing/bootstrap
commands that run on the host being installed.

Normal installed operation is UI-managed through Control -> Deployment and
Control -> Operations. The installer may use local privileged commands because
an operator runs it on the target host; the backend and browser must not become
a remote shell.

## Linux Master Artifact

The Linux master path is a systemd-owned appliance:

- `infra/install/systemd/vezor-master.service` owns the master service.
- `infra/install/compose/compose.master.yml` defines the product service set.
- `installer/linux/install-master.sh` validates the host, writes
  `/etc/vezor/master.json`, installs the systemd unit, and starts the service.
- `installer/linux/uninstall.sh` preserves data by default and requires the
  explicit confirmation string `delete-vezor-data` before removing state.

The package may use Docker or Podman under the hood, but the operator should
not run `make dev-up`, hand-run Compose, or paste bearer tokens for normal
operation.
