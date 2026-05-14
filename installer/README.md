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
