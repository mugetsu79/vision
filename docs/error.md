morya@printer vision % cd "$HOME/vision/backend"
ARGUS_API_BASE_URL="http://127.0.0.1:8000" \
ARGUS_API_BEARER_TOKEN="$TOKEN" \
ARGUS_DB_URL="postgresql+asyncpg://argus:argus@127.0.0.1:5432/argus" \
ARGUS_NATS_URL="nats://127.0.0.1:4222" \
ARGUS_MINIO_ENDPOINT="127.0.0.1:9000" \
ARGUS_MINIO_ACCESS_KEY="argus" \
ARGUS_MINIO_SECRET_KEY="argus-dev-secret" \
ARGUS_MINIO_SECURE="false" \
python3 -m uv run python -m argus.inference.engine --camera-id "876c8d43-3cd4-4cfa-8414-98b48666497b"
/Users/morya/vision/backend/.venv/lib/python3.12/site-packages/pydantic_settings/sources/providers/secrets.py:67: UserWarning: directory "/run/secrets" does not exist
  warnings.warn(f'directory "{path}" does not exist')
2026-04-20 21:09:28.377199 [W:onnxruntime:, coreml_execution_provider.cc:81 GetCapability] CoreMLExecutionProvider::GetCapability, number of partitions supported by CoreML: 30 number of nodes in the graph: 496 number of nodes supported by CoreML: 465
2026-04-20 21:09:28.929517 [W:onnxruntime:, session_state.cc:1166 VerifyEachNodeIsAssignedToAnEp] Some nodes were not assigned to the preferred execution providers which may or may not have an negative impact on performance. e.g. ORT explicitly assigns shape related ops to CPU to improve perf.
2026-04-20 21:09:28.929533 [W:onnxruntime:, session_state.cc:1168 VerifyEachNodeIsAssignedToAnEp] Rerunning with verbose output on a non-minimal build will show node assignments.
[ WARN:0@49.296] global cap_ffmpeg_impl.hpp:453 _opencv_ffmpeg_interrupt_callback Stream timeout triggered after 30000.004628 ms
[ WARN:0@110.647] global cap_ffmpeg_impl.hpp:453 _opencv_ffmpeg_interrupt_callback Stream timeout triggered after 30000.689365 ms
[h264 @ 0x7f94845bde00] left block unavailable for requested intra4x4 mode -1
[h264 @ 0x7f94845bde00] error while decoding MB 0 2, bytestream 3882

backend-1  | Failed to export span batch due to timeout, max retries or shutdown.
backend-1  | INFO:     172.18.0.13:47720 - "GET /metrics HTTP/1.1" 200 OK
backend-1  | INFO:     172.18.0.13:46826 - "GET /metrics HTTP/1.1" 200 OK
backend-1  | INFO:     172.18.0.13:46650 - "GET /metrics HTTP/1.1" 200 OK
backend-1  | INFO:     172.18.0.1:55282 - "GET /api/v1/cameras/876c8d43-3cd4-4cfa-8414-98b48666497b/worker-config HTTP/1.1" 200 OK
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 1.13s.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 2.20s.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 3.32s.
backend-1  | Failed to export span batch due to timeout, max retries or shutdown.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 1.11s.
backend-1  | INFO:     172.18.0.13:48818 - "GET /metrics HTTP/1.1" 200 OK
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 1.98s.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 4.35s.
backend-1  | Failed to export span batch due to timeout, max retries or shutdown.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 0.95s.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 2.32s.
backend-1  | Transient error HTTPConnectionPool(host='otel-collector', port=4318): Max retries exceeded with url: /v1/traces (Caused by NameResolutionError("HTTPConnection(host='otel-collector', port=4318): Failed to resolve 'otel-collector' ([Errno -2] Name or service not known)")) encountered while exporting span batch, retrying in 3.56s.
backend-1  | INFO:     172.18.0.13:57552 - "GET /metrics HTTP/1.1" 200 OK
backend-1  | Failed to export span batch due to timeout, max retries or shutdown.
morya@printer vision % 
