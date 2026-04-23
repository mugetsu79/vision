morya@printer backend % tail /tmp/argus-worker.log         
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=750 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 347.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=751 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=751 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=751 stage=detect details={'active_classes': ['person']}
morya@printer backend % cat /tmp/argus-worker.log
/Users/morya/vision/backend/.venv/lib/python3.12/site-packages/pydantic_settings/sources/providers/secrets.py:67: UserWarning: directory "/run/secrets" does not exist
  warnings.warn(f'directory "{path}" does not exist')
HTTP Request: GET http://127.0.0.1:8000/api/v1/cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/worker-config "HTTP/1.1 200 OK"
Resolved inference runtime policy profile=macos-x86_64-intel system=darwin machine=x86_64 cpu_vendor=intel detection_provider=CoreMLExecutionProvider attribute_provider=<disabled> provider_override=False profile_override=False available_providers=['CoreMLExecutionProvider', 'AzureExecutionProvider', 'CPUExecutionProvider']
2026-04-23 18:18:41.150683 [W:onnxruntime:, coreml_execution_provider.cc:81 GetCapability] CoreMLExecutionProvider::GetCapability, number of partitions supported by CoreML: 30 number of nodes in the graph: 496 number of nodes supported by CoreML: 465
2026-04-23 18:18:41.691363 [W:onnxruntime:, session_state.cc:1166 VerifyEachNodeIsAssignedToAnEp] Some nodes were not assigned to the preferred execution providers which may or may not have an negative impact on performance. e.g. ORT explicitly assigns shape related ops to CPU to improve perf.
2026-04-23 18:18:41.691376 [W:onnxruntime:, session_state.cc:1168 VerifyEachNodeIsAssignedToAnEp] Rerunning with verbose output on a non-minimal build will show node assignments.
Loaded detection model YOLO12n COCO iMac with provider CoreMLExecutionProvider
HTTP Request: POST http://localhost:9997/v3/config/paths/replace/cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated "HTTP/1.1 200 OK"
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=1 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 532.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=2 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 367.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=3 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 328.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=4 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 305.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=5 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 321.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=6 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 339.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=7 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 340.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=8 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=9 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 382.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=10 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=11 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=12 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 320.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=13 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 329.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=14 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 303.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=15 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=16 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=17 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 329.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=18 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 408.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=19 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=20 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 321.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=21 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 331.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=22 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 321.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=23 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=24 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=25 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 317.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=26 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 279.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=27 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 394.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=28 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=29 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 310.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=30 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=31 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 367.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=32 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=33 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=34 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=35 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=36 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 374.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=37 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=38 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 309.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=39 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 291.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=40 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=41 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 288.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=42 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 293.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=43 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=44 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 315.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=45 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 368.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=46 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=47 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 303.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=48 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 350.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=49 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 292.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=50 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 321.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=51 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=52 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 343.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=53 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 346.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=54 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 386.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=55 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 290.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=56 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=57 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 322.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=58 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 311.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=59 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 329.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=60 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=61 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 286.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=62 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=63 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 393.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=64 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 288.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=65 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=66 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 318.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=67 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 302.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=68 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 345.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=69 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=70 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 324.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=71 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 307.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=72 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 349.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=73 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 318.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=74 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 337.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=75 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=76 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=77 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 287.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=78 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 313.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=79 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 318.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=80 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 291.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=81 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 352.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=82 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 302.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=83 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 292.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=84 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 335.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=85 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 341.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=86 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 310.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=87 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 311.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=88 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 336.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=89 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=90 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 384.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=91 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=92 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 316.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=93 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 350.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=94 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=95 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=96 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 339.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=97 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 312.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=98 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 336.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=99 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 365.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=100 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=101 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=102 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=103 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=104 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 287.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=105 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 289.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=106 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 340.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=107 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 318.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=108 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 355.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=109 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=110 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 346.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=111 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=112 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 374.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=113 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 312.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=114 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 294.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=115 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 313.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=116 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=117 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 350.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=118 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=119 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Inference stage timing summary camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_count=120 stage_avg_ms={annotate=0.5, attributes=0.0, capture=19.3, detect=295.9, persist_tracking=0.0, preprocess=0.3, publish_stream=4.6, publish_telemetry=2.1, rules=0.0, speed=0.0, total=322.6, track=0.0, zones=0.0} stage_max_ms={annotate=1.2, attributes=0.0, capture=77.8, detect=438.8, persist_tracking=0.0, preprocess=1.6, publish_stream=88.0, publish_telemetry=3.4, rules=0.0, speed=0.0, total=532.8, track=0.0, zones=0.0}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=120 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=121 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 286.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=122 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=123 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=124 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=125 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 349.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=126 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 355.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=127 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 294.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=128 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 291.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=129 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=130 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=131 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 313.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=132 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 336.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=133 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 438.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=134 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 390.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=135 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 362.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=136 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 372.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=137 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=138 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=139 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 316.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=140 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 345.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=141 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 356.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=142 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 337.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=143 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 347.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=144 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 365.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=145 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=146 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=147 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=148 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 331.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=149 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=150 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=151 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 346.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=152 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=153 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 358.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=154 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=155 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 344.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=156 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 312.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=157 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=158 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 307.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=159 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 300.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=160 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=161 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=162 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 371.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=163 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=164 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 324.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=165 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 320.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=166 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 322.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=167 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 320.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=168 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 331.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=169 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 374.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=170 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 406.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=171 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 405.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=172 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 455.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=173 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 374.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=174 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 380.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=detect details={'detection_count': 1}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=175 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 474.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=176 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 326.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=177 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 305.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=178 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 334.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=179 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=180 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=181 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 353.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=182 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 309.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=183 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 364.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=184 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 302.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=185 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 321.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=186 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 307.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=187 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 302.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=188 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 322.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=189 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=190 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 357.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=191 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=192 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=193 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=194 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 300.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=195 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=196 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 335.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=197 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 317.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=198 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=199 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 360.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=200 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 300.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=201 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 364.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=202 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 350.7}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=203 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 301.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=204 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=205 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 309.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=206 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=207 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 348.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=208 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=209 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 316.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=210 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 334.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=211 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 340.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=212 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 323.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=213 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 332.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=214 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 333.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=215 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 330.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=216 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 319.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=217 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 367.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=218 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 304.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=219 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=220 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=221 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 325.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=222 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 316.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=223 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 303.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=224 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.1}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=225 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=226 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=227 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 382.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=228 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 302.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=229 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 306.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=230 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.8}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=231 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 298.4}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=232 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 308.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=233 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 295.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=234 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 358.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=235 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 317.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=236 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 385.6}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=237 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 296.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=238 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 318.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=239 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 311.3}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Inference stage timing summary camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_count=120 stage_avg_ms={annotate=0.5, attributes=0.0, capture=17.9, detect=296.3, persist_tracking=0.7, preprocess=0.2, publish_stream=3.8, publish_telemetry=2.2, rules=0.0, speed=0.0, total=327.9, track=6.4, zones=0.0} stage_max_ms={annotate=1.7, attributes=0.0, capture=61.7, detect=357.8, persist_tracking=87.8, preprocess=0.4, publish_stream=5.7, publish_telemetry=3.8, rules=0.0, speed=0.0, total=474.0, track=94.5, zones=0.0}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=240 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 300.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=241 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 299.2}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=242 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 335.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=243 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 313.0}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=244 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 297.5}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=245 stage=complete details={'stream_mode': 'annotated-whip', 'total_ms': 347.9}
Worker frame capture starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=capture details={}
Worker frame capture completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=capture details={'frame_shape': (720, 1280, 3)}
Worker frame detect starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=detect details={'active_classes': ['person']}
Worker frame detect completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=detect details={'detection_count': 0}
Worker frame publish_stream starting camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
Worker frame publish_stream completed camera_id=4f6380b8-75d6-4e92-90b8-d870f4ca06c0 frame_attempt=246 stage=publish_stream details={'stream_mode': 'annotated-whip', 'path_name': 'cameras/4f6380b8-75d6-4e92-90b8-d870f4ca06c0/annotated'}
