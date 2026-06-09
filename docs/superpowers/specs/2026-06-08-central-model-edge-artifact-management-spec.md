# Central Model, Artifact, and Edge Configuration Management Spec

**Date:** 2026-06-08

**Status:** Proposed

**Related Plan:** `docs/superpowers/plans/2026-06-08-central-model-edge-artifact-management-plan.md`

## Summary

After a master or edge installer completes, an operator should finish normal configuration from the Vezor UI. The edge host may still run a small installer to create the supervisor service, pair with the master, and install required system packages, but model downloads, model registration, model distribution, runtime artifact creation, TensorRT engine builds, validation, camera assignment, worker configuration, and routine edge configuration should be driven from the central control plane.

This spec extends the existing model catalog, model registry, runtime artifact registry, deployment node pairing, supervisor service reports, operations profiles, and worker lifecycle system. It adds a bounded central-to-edge job protocol for model distribution and artifact builds. The control plane stores desired state and audit history; the edge supervisor performs node-local privileged work such as downloading model files into the edge store, building TensorRT engines against the Jetson runtime, validating artifacts, and reporting inventory.

The key product rule is: TensorRT engines and exported runtime assets are not primary camera models. They are runtime artifacts derived from a registered model for a specific target profile, node, and sometimes scene vocabulary. Camera and scene setup continues to pick source models and runtime preferences; runtime selection chooses a valid artifact when available.

## Goals

- Let an admin download/register bundled catalog models, including `yolo26n` and `yolo26s`, from the UI.
- Let an admin add custom models from controlled sources without editing files or using the backend CLI.
- Let an admin assign registered models and runtime artifacts to a deployment node such as the Jetson validation edge.
- Let an admin create runtime artifacts from the UI:
  - fixed-vocab TensorRT engines derived from ONNX source models;
  - open-vocab scene ONNX exports;
  - open-vocab scene TensorRT engines.
- Let an admin validate artifact availability, hash, target profile, runtime versions, and source-model compatibility from the UI.
- Let the edge supervisor report model and artifact inventory, build status, validation status, and storage pressure.
- Let the central UI configure remaining routine edge settings after installer pairing.
- Preserve existing runtime selection semantics: model admission and worker config only use artifacts that are valid for the selected camera, vocabulary, target profile, and runtime preference.
- Avoid generic remote shell. Central commands must be typed, auditable jobs with bounded inputs and outputs.

## Non-Goals

- No arbitrary command execution from central to edge.
- No automatic external model marketplace with untrusted code execution.
- No silent TensorRT build on the master for an edge target. TensorRT builds must occur on the target node, or on a controlled build host with an explicitly matching target profile.
- No model deletion in this plan. Removal and garbage collection can be added after central distribution and artifact lifecycle are reliable.
- No replacement of existing worker lifecycle or runtime selection. The plan adds inventory and artifact build state that feeds those existing systems.

## Personas and Workflows

### Admin: Register Bundled Model

1. Open **Models**.
2. Select **Catalog**.
3. See `YOLO26n COCO` and `YOLO26s COCO` as available bundled/catalog entries.
4. Click **Register** if the local master already has the artifact.
5. Click **Download and register** if the artifact is missing but the catalog entry has a trusted source.
6. Watch progress.
7. See the model in **Registered models** with hash, size, license, capability, readiness, and source.

### Admin: Add Custom Model

1. Open **Models**.
2. Select **Add model**.
3. Choose **URL** or **local path on master**.
4. Provide name, version, task, format, expected SHA-256, license, capability, runtime backend hints, and input shape.
5. Start import.
6. See the model move through queued, downloading, verifying, registered, or failed states.

### Admin: Prepare Jetson Runtime

1. Open **Deployment**.
2. Select the Jetson edge node.
3. Open **Models and artifacts**.
4. Assign `YOLO26n COCO` and `YOLO26s COCO` to the Jetson.
5. Start a sync job.
6. The Jetson supervisor pulls assigned models from central or from an approved URL, verifies hash, stores them in the edge model store, and reports inventory.
7. UI shows synced or failed with specific evidence.

### Admin: Build TensorRT Engine

1. Open a registered ONNX model.
2. Click **Create runtime artifact**.
3. Pick **TensorRT engine**.
4. Pick target node **Jetson**.
5. Pick precision, input shape, workspace and builder options from constrained choices.
6. Start build.
7. The edge supervisor builds the engine locally, validates the file, reports runtime versions and metrics, and central registers a `ModelRuntimeArtifact` with target profile such as `linux-aarch64-nvidia-jetson`.
8. Runtime selection can now choose the TensorRT artifact for matching cameras and nodes.

### Admin: Build Scene Open-Vocab Artifact

1. Configure a camera/scene with an open-vocab model and runtime vocabulary.
2. Open **Models** or the scene setup panel.
3. Start **Create scene artifact** for the selected camera.
4. Pick target node and export formats: ONNX, TensorRT, or both.
5. Supervisor exports with the exact normalized vocabulary, validates the artifact, and reports vocabulary hash/version.
6. Central registers scene-scoped artifacts tied to the camera.
7. Runtime selection uses only artifacts matching the camera vocabulary hash.

### Operator: Configure Edge After Installer

1. Run the edge installer with API URL and pairing token.
2. Installer starts supervisor and reports service status.
3. Central UI configures:
   - site/node assignment;
   - labels and description;
   - model assignments;
   - camera assignments;
   - stream delivery profile;
   - worker concurrency and restart policy;
   - runtime preference;
   - storage and retention profile;
   - support bundle and remote support posture;
   - service-report cadence.
4. Supervisor polls desired state and applies supported settings.

## Architecture

### Control Plane

The master control plane owns:

- model catalog state;
- registered `Model` rows;
- `ModelRuntimeArtifact` rows;
- desired model assignments per deployment node;
- model import/download jobs;
- model sync jobs;
- runtime artifact build jobs;
- supervisor job queue state;
- edge configuration desired state;
- audit history and user-visible status.

The master never assumes an edge artifact is valid because a path string exists. It accepts artifact registration from an authenticated supervisor only when the job result contains source hash, artifact hash, size, target profile, runtime versions, validation status, and a path that is meaningful for the target node.

### Edge Supervisor

The supervisor owns node-local actions:

- reporting hardware and runtime profile;
- pulling assigned model files into the node model store;
- verifying SHA-256 and file size;
- building TensorRT engines against installed CUDA/TensorRT providers;
- exporting open-vocab scene artifacts against node-local source models;
- validating artifacts;
- reporting model/artifact inventory;
- applying bounded configuration profiles;
- restarting managed services when a supported configuration changes.

The supervisor must not execute arbitrary scripts supplied by the control plane. Jobs are typed and validated.

### Job Protocol

The system uses a pull-first job protocol so Jetson nodes behind NAT can operate without inbound access. Central creates jobs. Supervisors poll jobs with node credentials. Each job includes:

- job type;
- target deployment node;
- payload version;
- bounded input payload;
- desired asset/model/artifact IDs;
- idempotency key;
- state;
- progress events;
- timestamps;
- actor subject.

Supervisors report events:

- `queued`;
- `accepted`;
- `downloading`;
- `verifying`;
- `building`;
- `validating`;
- `completed`;
- `failed`;
- `cancelled`.

Completed artifact-build jobs may create or update a `ModelRuntimeArtifact` centrally. Completed sync jobs update edge inventory.

### Data Model Additions

The plan should add these concepts:

- `ModelImportJob`: central model download/import lifecycle.
- `DeploymentModelAssignment`: desired model presence on a deployment node.
- `DeploymentModelSyncJob`: supervisor-executed model distribution lifecycle.
- `DeploymentModelInventory`: supervisor-reported model/artifact inventory.
- `RuntimeArtifactBuildJob`: desired runtime artifact build lifecycle.
- `SupervisorModelJobEvent`: append-only progress and audit events for model/artifact jobs.
- `EdgeConfigurationAssignment`: desired node configuration profile and applied revision.

Existing `Model`, `ModelRuntimeArtifact`, `DeploymentNode`, `SupervisorServiceStatusReport`, operator config profiles, hardware reports, and worker lifecycle requests remain the source of truth for their current responsibilities.

### API Surface

Admin/control-plane endpoints:

- `GET /api/v1/model-catalog`
- `POST /api/v1/model-catalog/{catalog_id}/download`
- `POST /api/v1/model-catalog/{catalog_id}/register`
- `GET /api/v1/model-import-jobs`
- `POST /api/v1/models/import-url`
- `GET /api/v1/models/{model_id}/runtime-artifacts`
- `POST /api/v1/models/{model_id}/runtime-artifact-build-jobs`
- `GET /api/v1/models/{model_id}/runtime-artifact-build-jobs`
- `GET /api/v1/deployment/nodes/{node_id}/model-assignments`
- `POST /api/v1/deployment/nodes/{node_id}/model-assignments`
- `DELETE /api/v1/deployment/nodes/{node_id}/model-assignments/{assignment_id}`
- `POST /api/v1/deployment/nodes/{node_id}/model-sync-jobs`
- `GET /api/v1/deployment/nodes/{node_id}/model-inventory`
- `GET /api/v1/deployment/nodes/{node_id}/edge-configuration`
- `PUT /api/v1/deployment/nodes/{node_id}/edge-configuration`

Supervisor endpoints:

- `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/poll`
- `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/{job_id}/events`
- `POST /api/v1/deployment/supervisors/{supervisor_id}/model-jobs/{job_id}/complete`
- `POST /api/v1/deployment/supervisors/{supervisor_id}/model-inventory`
- `GET /api/v1/model-assets/{asset_id}/download`
- `POST /api/v1/deployment/supervisors/{supervisor_id}/edge-configuration/apply-report`

All supervisor endpoints must authenticate by node credential or admin and must enforce that the authenticated node can only operate on its own jobs and inventory.

## UI

### Models Page

The Models page should include:

- Catalog tab: curated entries, readiness, license, model family, capability, local artifact state, register/download actions.
- Registered tab: installed models with hash, size, path, capability, source, and runtime artifacts.
- Imports tab: queued/running/failed/succeeded import jobs.
- Runtime artifacts tab: model-scoped and scene-scoped artifacts with target profile, precision, source hash, validation status, and node association.
- Edge distribution tab: deployment-node assignments, sync state, and inventory.

### Deployment Node Detail

Deployment node rows or detail panels should include:

- model assignment controls;
- model/artifact inventory;
- artifact build actions;
- edge configuration profile;
- service report diagnostics;
- support bundle link.

### Scene Setup

Camera and scene setup should surface:

- whether the selected model is registered;
- whether the target node has the model synced;
- whether a runtime artifact exists for the selected runtime preference;
- whether a scene-scoped open-vocab artifact is stale because vocabulary changed;
- a direct action to build the missing artifact.

Readiness text must distinguish missing model, unsynced edge model, missing artifact, stale artifact, unsupported target profile, and failed build.

## Edge Configuration From Central

The central UI should manage these post-install fields:

- node display name, description, labels;
- site assignment;
- time zone inherited from site;
- master API URL and central stream URL observed by supervisor;
- model store path and max bytes;
- artifact store path and max bytes;
- worker concurrency;
- runtime preference profile;
- fallback policy;
- service report interval;
- hardware report interval;
- support bundle collection policy;
- stream delivery profile;
- local MediaMTX WebRTC advertised hosts/origins;
- NATS/leaf or operations polling mode;
- evidence retention profile;
- incident upload policy;
- privacy profile;
- camera-to-node assignments;
- desired worker state.

Installer-only data should be limited to OS packages, Docker/runtime prerequisites, service manager installation, supervisor credential/pairing, and the minimum local defaults required to contact the master.

## Security and Safety

- Catalog downloads use trusted catalog metadata and expected checksums.
- Custom model URL import is admin-only and should require checksum before production use.
- Upload support stores files in a controlled model store and computes checksum before registration.
- The edge supervisor receives signed, short-lived asset download URLs or node-scoped asset references.
- Runtime artifact build options are constrained enums, not free-form commands.
- Job payloads include schema version and idempotency key.
- Every admin action emits audit metadata: actor subject, tenant, node, model, artifact, job id, timestamp.
- Node credentials can only poll/report jobs for their deployment node.
- Artifact registration rejects source hash mismatch, stale vocabulary hash, wrong target node, and wrong target profile.
- Failures must be visible with concrete error messages, not collapsed into "needs setup".

## Acceptance Criteria

- A clean master install can complete first-run and show `YOLO26n COCO` and `YOLO26s COCO` in the model catalog.
- An admin can register bundled `yolo26n` and `yolo26s` from the UI when artifacts are present.
- An admin can start a model download/import from UI and see progress and final hash.
- An admin can assign a registered model to the Jetson edge node from UI.
- A paired Jetson supervisor can poll the assignment, download or pull the model into the edge model store, verify hash, and report inventory.
- An admin can request a TensorRT engine build from the UI for a Jetson target.
- The Jetson builds and validates the engine, central records a valid model-scoped runtime artifact, and runtime selection can use it for matching camera workers.
- An admin can request an open-vocab scene artifact for a camera with runtime vocabulary.
- Vocabulary changes mark old open-vocab scene artifacts stale and offer a rebuild action.
- Deployment UI can update central-managed edge configuration and show applied revision or failure.
- No manual edge CLI is required after installer pairing for routine model, artifact, worker, stream, or support-bundle configuration.
- Docs explain master install, edge install, UI-driven model registration, UI-driven artifact build, model assignment, and validation smoke.
