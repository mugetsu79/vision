# Live Video Troubleshooting

Use this when the Live page shows a scene as running, but the video is blank after a rebuild, redeploy, or network interruption.

## Quick Recovery

1. Refresh the Live page once. If telemetry and video do not return within a few seconds, continue below.
2. Open Operations, find the scene under Scene workers, and use Restart. You do not need to re-bind the worker if an active assignment already exists.
3. If the scene has no active worker assignment in Operations, bind or assign the worker first, then restart it.

## Check The Running Master

Confirm the local stack is healthy:

```sh
docker ps --filter name=vezor-master
curl -fsS http://127.0.0.1:8000/healthz
```

Check whether MediaMTX has a ready stream path:

```sh
curl -s http://127.0.0.1:9997/v3/paths/list
```

Healthy video usually has the scene path marked ready or online, an H264 track, and inbound bytes increasing. If the path is missing or not ready, the worker is not publishing usable video yet.

Check whether the supervisor container has the worker and ffmpeg processes:

```sh
docker exec vezor-master-vezor-supervisor-1 /bin/sh -lc 'for f in /proc/[0-9]*/cmdline; do c=$(tr "\0" " " < "$f" 2>/dev/null); case "$c" in *argus.inference*|*ffmpeg*) echo "${f%/cmdline}:$c";; esac; done'
```

Expected result: one `argus.inference.engine` process and one `ffmpeg` process for the active scene stream.

Check worker assignments:

```sh
docker exec vezor-master-postgres-1 psql -U argus -d argus -c "select c.name, wa.id, wa.desired_state, wa.active from worker_assignments wa join cameras c on c.id = wa.camera_id order by wa.updated_at desc;"
```

If there is an active assignment but no worker process or no ready MediaMTX path, restart the worker. A stale runtime report can still say running; trust the child process list and MediaMTX path readiness for recovery.

## Check Live Rendition Changes

Use this when changing the Live page rendition, for example from `annotated` to
`240p5`, does not appear to change the stream.

Confirm the camera saved the selected profile:

```sh
docker exec vezor-master-postgres-1 psql -U argus -d argus -c "
select name, browser_delivery->>'default_profile' as default_profile
from cameras
order by updated_at desc;"
```

Confirm MediaMTX has the matching profile-specific path. Reduced processed
renditions use `annotated-PROFILE`, so `240p5` should appear as
`annotated-240p5` and report an H264 track near `426x240`.

```sh
curl -s http://127.0.0.1:9997/v3/paths/list
```

If the database shows the new profile but MediaMTX still shows only the old
path, restart the scene worker from Operations. The worker should then fetch the
latest worker config and publish the selected rendition.

If MediaMTX shows the new path as ready but the browser still displays the old
stream, refresh the Live page once. The Live tile should reconnect with the new
profile badge and the new WebRTC/HLS session.

## Jetson Edge Notes

For Jetson-owned scenes, the same profile flow applies, but the first MediaMTX
check happens on the Jetson because the edge worker publishes into the Jetson
MediaMTX service:

```sh
ssh JETSON_HOST
docker ps --filter name=vezor
curl -s http://127.0.0.1:9997/v3/paths/list
docker logs --tail 120 vezor-supervisor
```

Healthy Jetson reduced renditions should show a ready path such as
`annotated-240p5`, an H264 track with the requested resolution, and no repeated
worker restart or worker-config errors in `vezor-supervisor`. If scene privacy
filtering is enabled on a Jetson-owned camera, expect the processed path to use
`preview-240p5` instead of `annotated-240p5`; the dimensions and FPS should
still match the selected profile.

From the master, confirm the edge supervisor is reporting the public Jetson
stream base URL and the camera is assigned to that edge node:

```sh
docker exec vezor-master-postgres-1 psql -U argus -d argus -c "
select c.name, c.processing_mode, c.edge_node_id, wa.active
from cameras c
left join worker_assignments wa on wa.camera_id = c.id and wa.active = true
order by c.updated_at desc;"
```

If the Jetson was already paired and only the source checkout changed, rerun the
edge installer as an unpaired update so the supervisor image, MediaMTX config,
and local compose environment all match the branch:

```sh
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-live-video-window-sizing
git pull --ff-only origin codex/omnisight-live-video-window-sizing

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

Use a fresh pairing session instead of `--unpaired` if
`/etc/vezor/supervisor.json` does not already contain an `edge_node_id`.

## CLI Restart Fallback

If the UI restart is not available, queue a lifecycle restart request. Replace `Office` with the scene name:

```sh
docker exec vezor-master-postgres-1 psql -U argus -d argus -c "
insert into operations_lifecycle_requests (
  id, tenant_id, camera_id, edge_node_id, assignment_id, action, status,
  requested_by_subject, requested_at, request_payload, created_at, updated_at
)
select gen_random_uuid(), wa.tenant_id, wa.camera_id, wa.edge_node_id, wa.id,
  'restart', 'requested', 'local-maintenance', now(),
  jsonb_build_object(
    'source', 'manual-live-video-recovery',
    'dispatch_mode', 'polling',
    'dispatch_status', 'queued_for_polling'
  ),
  now(), now()
from worker_assignments wa
join cameras c on c.id = wa.camera_id
where wa.active = true and c.name = 'Office'
returning id, action, status, assignment_id;"
```

After the request completes, verify MediaMTX again and refresh the Live page.
