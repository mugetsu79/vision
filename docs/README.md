# Vezor Documentation

This directory is the operator-facing documentation set for Vezor 2026.1. Start
here when installing, operating, or validating the product.

## Start Here

- [Vezor User Guide](vezor-user-guide.md): daily operator workflow for Live,
  Scenes, Evidence, Models, Links, Deployment, Operations, and Users.
- [Full Installation Guide](full-installation-guide.md): fresh master and
  Jetson edge installation, first-run bootstrap, platform superadmin bootstrap,
  pairing, model registration, TensorRT artifacts, and smoke validation.
- [Admin And Operations Guide](admin-and-operations-guide.md): tenants, users,
  roles, readiness, worker lifecycle, support bundles, Core Link, and common
  operating decisions.
- [Release Notes 2026.1](release-notes/2026.1.md): first release highlights,
  supported paths, known limits, and upgrade notes.

## Deep References

- [Product Installer And First-Run Guide](product-installer-and-first-run-guide.md):
  expanded installer reference and break-glass procedures.
- [Operator Deployment Playbook](operator-deployment-playbook.md): deployment
  modes, validation posture, and pilot rollout details.
- [Runbook](runbook.md): operational commands, troubleshooting, and recovery
  procedures.
- [Model Loading And Configuration Guide](model-loading-and-configuration-guide.md):
  model catalog, import, runtime artifact, and edge distribution details.
- [Core Link Performance Guide](core-link-performance-guide.md): link path,
  monitoring target, edge-agent, reflector, and throughput measurement model.
- [Live Video Troubleshooting](live-video-troubleshooting.md): blank video,
  stream readiness, worker, and browser delivery checks.
- [Scene Vision Profile Configuration Guide](scene-vision-profile-configuration-guide.md):
  scene profile, class scope, privacy, and tracking behavior.

## Screenshot Policy

Screenshots under `docs/assets/screenshots/` are captured from the live product
UI and sanitized before use. Do not commit screenshots that reveal:

- raw RTSP credentials or camera URLs
- bearer, bootstrap, node, reflector, or admin tokens
- sudo passwords
- private customer or operator identity values
- unredacted support bundle logs
