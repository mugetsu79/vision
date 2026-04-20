morya@printer backend % ffmpeg -rtsp_transport tcp -i "rtsp://admin:787469@192.168.1.175:554/live/profile.1" -f null -

ffmpeg version 8.1 Copyright (c) 2000-2026 the FFmpeg developers
  built with Apple clang version 16.0.0 (clang-1600.0.26.6)
  configuration: --prefix=/usr/local/Cellar/ffmpeg/8.1_1 --enable-shared --enable-pthreads --enable-version3 --cc=clang --host-cflags= --host-ldflags= --enable-ffplay --enable-gpl --enable-libsvtav1 --enable-libopus --enable-libx264 --enable-libmp3lame --enable-libdav1d --enable-libvmaf --enable-libvpx --enable-libx265 --enable-openssl --enable-videotoolbox --enable-audiotoolbox
  libavutil      60. 26.100 / 60. 26.100
  libavcodec     62. 28.100 / 62. 28.100
  libavformat    62. 12.100 / 62. 12.100
  libavdevice    62.  3.100 / 62.  3.100
  libavfilter    11. 14.100 / 11. 14.100
  libswscale      9.  5.100 /  9.  5.100
  libswresample   6.  3.100 /  6.  3.100
Input #0, rtsp, from 'rtsp://admin:787469@192.168.1.175:554/live/profile.1':
  Metadata:
    title           : Session streamed by D-Link
    comment         : live/profile.1
  Duration: N/A, start: 0.000000, bitrate: N/A
  Stream #0:0: Video: h264 (High), yuvj420p(pc, bt709, progressive), 1280x720, 15 fps, 25 tbr, 90k tbn, start 0.040000
  Stream #0:1: Audio: aac (LC), 16000 Hz, mono, fltp
Stream mapping:
  Stream #0:0 -> #0:0 (h264 (native) -> wrapped_avframe (native))
  Stream #0:1 -> #0:1 (aac (native) -> pcm_s16le (native))
Press [q] to stop, [?] for help
Output #0, null, to 'pipe:':
  Metadata:
    title           : Session streamed by D-Link
    comment         : live/profile.1
    encoder         : Lavf62.12.100
  Stream #0:0: Video: wrapped_avframe, yuvj420p(pc, bt709, progressive), 1280x720, q=2-31, 200 kb/s, 15 fps, 15 tbn
    Metadata:
      encoder         : Lavc62.28.100 wrapped_avframe
  Stream #0:1: Audio: pcm_s16le, 16000 Hz, mono, s16, 256 kb/s
    Metadata:
      encoder         : Lavc62.28.100 pcm_s16le
[out#0/null @ 0x7fd6a380c200] video:75KiB audio:398KiB subtitle:0KiB other streams:0KiB global headers:0KiB muxing overhead: unknown
frame=  182 fps= 18 q=-0.0 Lsize=N/A time=00:00:12.13 bitrate=N/A speed=1.17x elapsed=0:00:10.34    
Exiting normally, received signal 2.
morya@printer backend % cd "$HOME/vision/backend"
OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" \
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
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/Users/morya/vision/backend/src/argus/inference/engine.py", line 754, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/Users/morya/vision/backend/src/argus/inference/engine.py", line 739, in main
    asyncio.run(run_engine_for_camera(args.camera_id))
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "/Users/morya/vision/backend/src/argus/inference/engine.py", line 647, in run_engine_for_camera
    config = await load_engine_config(camera_id, settings=resolved_settings)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/morya/vision/backend/src/argus/inference/engine.py", line 532, in load_engine_config
    response.raise_for_status()
  File "/Users/morya/vision/backend/.venv/lib/python3.12/site-packages/httpx/_models.py", line 829, in raise_for_status
    raise HTTPStatusError(message, request=request, response=self)
httpx.HTTPStatusError: Client error '401 Unauthorized' for url 'http://127.0.0.1:8000/api/v1/cameras/876c8d43-3cd4-4cfa-8414-98b48666497b/worker-config'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401
morya@printer backend % 
