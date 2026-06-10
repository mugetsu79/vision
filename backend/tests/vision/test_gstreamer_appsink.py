from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest
from numpy.typing import NDArray

from argus.vision.gstreamer_appsink import (
    AppSinkPipelineMode,
    AppSinkRuntime,
    GStreamerAppSinkCapture,
    PyGObjectAppSinkRuntime,
    build_rtsp_appsink_pipeline,
    probe_appsink_capabilities,
    redact_pipeline,
)

Frame = NDArray[np.uint8]


def _credentialed_rtsp_uri(*, include_jwt: bool = False) -> tuple[str, str, str]:
    credential = "user" + ":" + "pass"
    jwt = "secret" + "-" + "token"
    uri = f"rtsp://{credential}@camera.internal:8554/ch2"
    if include_jwt:
        uri = f"{uri}?jwt={jwt}&profile=main"
    return uri, credential, jwt


def test_native_pipeline_uses_nvidia_decode_resize_and_single_frame_sink() -> None:
    source_uri, _, _ = _credentialed_rtsp_uri()

    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=AppSinkPipelineMode.JETSON_NATIVE,
        target_width=1280,
        target_height=720,
        protocols="tcp",
        latency_ms=80,
        drop_on_latency=True,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=True,
    )

    assert f'rtspsrc location="{source_uri}"' in pipeline
    assert "protocols=tcp" in pipeline
    assert "latency=80" in pipeline
    assert "drop-on-latency=true" in pipeline
    assert "rtph264depay ! h264parse ! nvv4l2decoder disable-dpb=true" in pipeline
    assert (
        "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream"
        in pipeline
    )
    assert (
        "nvvidconv ! video/x-raw,format=BGRx,width=1280,height=720 ! videoconvert"
        in pipeline
    )
    assert "videoconvert ! video/x-raw,format=BGR ! appsink" in pipeline
    assert (
        "appsink name=sink sync=false max-buffers=1 drop=true emit-signals=false"
        in pipeline
    )
    assert "leaky-type=downstream" not in pipeline


def test_software_pipeline_uses_software_decode_and_leaky_appsink() -> None:
    pipeline = build_rtsp_appsink_pipeline(
        "rtsp://camera.internal/live",
        mode=AppSinkPipelineMode.GSTREAMER_SOFTWARE,
        target_width=640,
        target_height=360,
        protocols="tcp",
        latency_ms=120,
        drop_on_latency=False,
        appsink_supports_leaky_type=True,
        decoder_supports_disable_dpb=True,
    )

    assert "avdec_h264" in pipeline
    assert "nvv4l2decoder" not in pipeline
    assert "nvvidconv" not in pipeline
    assert "drop-on-latency=false" in pipeline
    assert (
        "avdec_h264 ! queue max-size-buffers=1 max-size-bytes=0 "
        "max-size-time=0 leaky=downstream ! videoconvert ! videoscale ! "
        "video/x-raw,format=BGR,width=640,height=360"
    ) in pipeline
    assert "leaky-type=downstream" in pipeline


def test_software_pipeline_omits_videoscale_and_dimensions_without_resize() -> None:
    pipeline = build_rtsp_appsink_pipeline(
        "rtsp://camera.internal/live",
        mode=AppSinkPipelineMode.GSTREAMER_SOFTWARE,
        target_width=None,
        target_height=None,
        protocols="tcp",
        latency_ms=120,
        drop_on_latency=False,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=False,
    )

    assert (
        "avdec_h264 ! queue max-size-buffers=1 max-size-bytes=0 "
        "max-size-time=0 leaky=downstream ! videoconvert ! "
        "video/x-raw,format=BGR ! appsink"
    ) in pipeline
    assert "videoscale" not in pipeline
    assert "width=" not in pipeline
    assert "height=" not in pipeline


def test_pipeline_quotes_and_escapes_injection_like_source_location() -> None:
    source_uri = 'rtsp://camera.internal/live path?profile="main"\\trail ! fakesink'

    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=AppSinkPipelineMode.GSTREAMER_SOFTWARE,
        target_width=None,
        target_height=None,
        protocols="tcp",
        latency_ms=120,
        drop_on_latency=False,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=False,
    )

    assert (
        'rtspsrc location="rtsp://camera.internal/live path?profile=\\"main\\"'
        '\\\\trail ! fakesink" protocols=tcp '
    ) in pipeline


@pytest.mark.parametrize(
    "protocols",
    ["tcp udp", "tcp ! fakesink", "tcp;filesrc", "tcp\nudp"],
)
def test_pipeline_rejects_invalid_protocols(protocols: str) -> None:
    with pytest.raises(ValueError, match="protocols"):
        build_rtsp_appsink_pipeline(
            "rtsp://camera.internal/live",
            mode=AppSinkPipelineMode.GSTREAMER_SOFTWARE,
            target_width=None,
            target_height=None,
            protocols=protocols,
            latency_ms=120,
            drop_on_latency=False,
            appsink_supports_leaky_type=False,
            decoder_supports_disable_dpb=False,
        )


def test_redact_pipeline_removes_rtsp_credentials_and_jwt_from_location() -> None:
    source_uri, credential, jwt = _credentialed_rtsp_uri(include_jwt=True)
    pipeline = build_rtsp_appsink_pipeline(
        source_uri,
        mode=AppSinkPipelineMode.JETSON_NATIVE,
        target_width=1280,
        target_height=720,
        protocols="tcp",
        latency_ms=80,
        drop_on_latency=True,
        appsink_supports_leaky_type=False,
        decoder_supports_disable_dpb=False,
    )

    redacted = redact_pipeline(pipeline)

    assert credential not in redacted
    assert jwt not in redacted
    assert (
        'location="rtsp://redacted@camera.internal:8554/ch2'
        '?jwt=redacted&profile=main"'
    ) in redacted


def test_redact_pipeline_removes_secrets_from_quoted_location_with_spaces() -> None:
    credential = "user" + ":" + "pass"
    jwt = "secret" + "-" + "token"
    pipeline = (
        f'rtspsrc location="rtsp://{credential}@camera.internal/live path'
        f'?jwt={jwt}&profile=main" protocols=tcp ! appsink name=sink'
    )

    redacted = redact_pipeline(pipeline)

    assert credential not in redacted
    assert jwt not in redacted
    assert (
        'location="rtsp://redacted@camera.internal/live path'
        '?jwt=redacted&profile=main"'
    ) in redacted


class _FakeSample:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload


class _FakeRuntime:
    def __init__(self, samples: list[_FakeSample | None]) -> None:
        self.samples = samples
        self.started_pipeline: str | None = None
        self.stopped = False
        self.stop_calls = 0

    def start(self, pipeline: str) -> None:
        self.started_pipeline = pipeline

    def pull_sample(self, timeout_s: float) -> _FakeSample | None:
        del timeout_s
        return self.samples.pop(0) if self.samples else None

    def sample_to_bgr(
        self,
        sample: object,
        *,
        width: int,
        height: int,
    ) -> Frame:
        fake_sample = cast(_FakeSample, sample)
        return np.frombuffer(fake_sample.payload, dtype=np.uint8).reshape(
            (height, width, 3),
        ).copy()

    def stop(self) -> None:
        self.stopped = True
        self.stop_calls += 1


def test_appsink_capture_returns_latest_bgr_frame_and_backend_mode() -> None:
    frame = np.arange(2 * 3 * 3, dtype=np.uint8).reshape((2, 3, 3))
    runtime = _FakeRuntime([_FakeSample(frame.tobytes())])
    capture = GStreamerAppSinkCapture.create(
        pipeline="fake-pipeline",
        runtime=runtime,
        width=3,
        height=2,
        media_pipeline_mode="jetson_gstreamer_native",
        read_timeout_s=0.01,
    )

    ok, observed = capture.read()

    assert ok is True
    assert observed is not None
    np.testing.assert_array_equal(observed, frame)
    assert runtime.started_pipeline == "fake-pipeline"
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"
    assert capture.media_capture_backend() == "gstreamer_appsink"
    assert set(capture.last_stage_timings()) == {"wait", "decode_read"}


def test_appsink_capture_reports_no_frame_when_sample_timeout_expires() -> None:
    runtime = _FakeRuntime([None])
    capture = GStreamerAppSinkCapture.create(
        pipeline="fake-pipeline",
        runtime=runtime,
        width=3,
        height=2,
        media_pipeline_mode="jetson_gstreamer_native",
        read_timeout_s=0.01,
    )

    ok, frame = capture.read()

    assert ok is False
    assert frame is None
    assert capture.last_stage_timings()["wait"] >= 0.0


def test_appsink_capture_release_stops_runtime_once() -> None:
    runtime = _FakeRuntime([])
    capture = GStreamerAppSinkCapture.create(
        pipeline="fake-pipeline",
        runtime=runtime,
        width=3,
        height=2,
        media_pipeline_mode="jetson_gstreamer_native",
        read_timeout_s=0.01,
    )

    capture.release()
    capture.release()

    assert runtime.stopped is True
    assert runtime.stop_calls == 1


def test_appsink_capture_create_validates_dimensions_before_starting_runtime() -> None:
    runtime = _FakeRuntime([])

    with pytest.raises(ValueError, match="width"):
        GStreamerAppSinkCapture.create(
            pipeline="fake-pipeline",
            runtime=runtime,
            width=0,
            height=2,
            media_pipeline_mode="jetson_gstreamer_native",
            read_timeout_s=0.01,
        )

    assert runtime.started_pipeline is None
    assert runtime.stopped is False


def test_appsink_capture_create_stops_runtime_when_construction_fails() -> None:
    class _FailingCapture(GStreamerAppSinkCapture):
        def __init__(
            self,
            *,
            runtime: AppSinkRuntime,
            width: int,
            height: int,
            media_pipeline_mode: str,
            read_timeout_s: float,
        ) -> None:
            del runtime, width, height, media_pipeline_mode, read_timeout_s
            raise RuntimeError("construction exploded")

    runtime = _FakeRuntime([])

    with pytest.raises(RuntimeError, match="construction exploded"):
        _FailingCapture.create(
            pipeline="fake-pipeline",
            runtime=runtime,
            width=3,
            height=2,
            media_pipeline_mode="jetson_gstreamer_native",
            read_timeout_s=0.01,
        )

    assert runtime.started_pipeline == "fake-pipeline"
    assert runtime.stopped is True
    assert runtime.stop_calls == 1


def test_probe_reports_unavailable_when_gi_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_import(name: str, package: str | None = None) -> object:
        del package
        if name == "gi":
            raise ImportError("missing gi")
        raise AssertionError(name)

    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        fail_import,
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == "missing gi"


def test_probe_checks_required_elements_and_optional_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _FakeGstRegistry(_available_appsink_features())
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is True
    assert caps.appsink_supports_leaky_type is True
    assert caps.decoder_supports_disable_dpb is True
    assert fake_gst.init_args == [None]


def test_probe_imports_gst_modules_directly_after_requiring_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _FakeGstRegistry(_available_appsink_features())
    fake_gst = _FakeProbeGst(registry)
    import_names: list[str] = []
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst, import_names=import_names),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is True
    assert import_names[:3] == ["gi", "gi.repository.Gst", "gi.repository.GstApp"]


def test_probe_native_is_available_without_software_decoder_or_scaler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    del features["avdec_h264"]
    del features["videoscale"]
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is True
    assert caps.decoder_supports_disable_dpb is True


def test_probe_software_is_available_without_nvidia_elements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    del features["nvv4l2decoder"]
    del features["nvvidconv"]
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities(AppSinkPipelineMode.GSTREAMER_SOFTWARE)

    assert caps.available is True
    assert caps.appsink_supports_leaky_type is True
    assert caps.decoder_supports_disable_dpb is False


def test_probe_software_ignores_broken_native_decoder_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    features["nvv4l2decoder"] = _FakeElementFactory(
        create_error=RuntimeError("native factory exploded"),
    )
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities(AppSinkPipelineMode.GSTREAMER_SOFTWARE)

    assert caps.available is True
    assert caps.appsink_supports_leaky_type is True
    assert caps.decoder_supports_disable_dpb is False


def test_probe_software_reports_missing_software_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    del features["avdec_h264"]
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities(AppSinkPipelineMode.GSTREAMER_SOFTWARE)

    assert caps.available is False
    assert caps.reason == "missing GStreamer elements: avdec_h264"


def test_probe_software_reports_missing_videoscale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    del features["videoscale"]
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities(AppSinkPipelineMode.GSTREAMER_SOFTWARE)

    assert caps.available is False
    assert caps.reason == "missing GStreamer elements: videoscale"


def test_probe_reports_missing_required_elements(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _FakeGstRegistry({"rtspsrc": _FakeElementFactory()})
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == (
        "missing GStreamer elements: rtph264depay, h264parse, queue, appsink, "
        "videoconvert, nvv4l2decoder, nvvidconv"
    )


@pytest.mark.parametrize("missing_element", ["nvvidconv", "videoconvert"])
def test_probe_reports_unavailable_when_generated_pipeline_element_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    missing_element: str,
) -> None:
    features = _available_appsink_features()
    del features[missing_element]
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == f"missing GStreamer elements: {missing_element}"


def test_probe_reports_unavailable_when_gst_init_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = _FakeGstRegistry(_available_appsink_features())
    fake_gst = _FakeProbeGst(registry, init_error=RuntimeError("init exploded"))
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == "init exploded"


def test_probe_reports_unavailable_when_registry_access_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_gst = _FakeProbeGst(
        _FakeGstRegistry(_available_appsink_features()),
        registry_error=RuntimeError("registry exploded"),
    )
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == "registry exploded"


def test_probe_reports_unavailable_when_optional_property_check_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = _available_appsink_features()
    features["appsink"] = _FakeElementFactory(create_error=RuntimeError("create exploded"))
    registry = _FakeGstRegistry(features)
    fake_gst = _FakeProbeGst(registry)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    caps = probe_appsink_capabilities()

    assert caps.available is False
    assert caps.reason == "create exploded"


def test_pygobject_runtime_starts_pulls_maps_bgr_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.arange(2 * 3 * 3, dtype=np.uint8).reshape((2, 3, 3))
    buffer = _FakeGstBuffer(frame.tobytes())
    sample = _FakeGstSample(buffer)
    sink = _FakeGstSink(sample)
    pipeline = _FakeGstPipeline(sink)
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )

    runtime = PyGObjectAppSinkRuntime()
    runtime.start("fake ! appsink name=sink")
    pulled = runtime.pull_sample(0.25)
    observed = runtime.sample_to_bgr(pulled, width=3, height=2)
    runtime.stop()

    assert fake_gst.launches == ["fake ! appsink name=sink"]
    assert pipeline.states == [fake_gst.State.PLAYING, fake_gst.State.NULL]
    assert sink.emits == [("try-pull-sample", 250_000_000)]
    assert buffer.map_flags == [fake_gst.MapFlags.READ]
    assert buffer.unmapped is True
    assert observed.flags.owndata is True
    np.testing.assert_array_equal(observed, frame)


def test_pygobject_runtime_imports_gst_modules_directly_after_requiring_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = _FakeGstPipeline(_FakeGstSink(None))
    fake_gst = _FakeRuntimeGst(pipeline)
    import_names: list[str] = []
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst, import_names=import_names),
    )

    PyGObjectAppSinkRuntime()

    assert import_names[:3] == ["gi", "gi.repository.Gst", "gi.repository.GstApp"]


def test_pygobject_runtime_copies_padded_bgr_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = bytes(
        [
            1,
            2,
            3,
            4,
            5,
            6,
            99,
            99,
            7,
            8,
            9,
            10,
            11,
            12,
            88,
            88,
        ],
    )
    expected = np.array(
        [
            [[1, 2, 3], [4, 5, 6]],
            [[7, 8, 9], [10, 11, 12]],
        ],
        dtype=np.uint8,
    )
    buffer = _FakeGstBuffer(payload)
    sample = _FakeGstSample(buffer)
    pipeline = _FakeGstPipeline(_FakeGstSink(sample))
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    observed = runtime.sample_to_bgr(sample, width=2, height=2)

    assert observed.flags.owndata is True
    np.testing.assert_array_equal(observed, expected)


def test_pygobject_runtime_rejects_padded_bgr_length_not_divisible_by_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = bytes(range(13))
    buffer = _FakeGstBuffer(payload)
    sample = _FakeGstSample(buffer)
    pipeline = _FakeGstPipeline(_FakeGstSink(sample))
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    with pytest.raises(RuntimeError, match="Unexpected GStreamer appsink buffer size 13"):
        runtime.sample_to_bgr(sample, width=2, height=2)


def test_pygobject_runtime_rejects_padded_bgr_row_stride_shorter_than_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = bytes(range(16))
    buffer = _FakeGstBuffer(payload)
    sample = _FakeGstSample(buffer)
    pipeline = _FakeGstPipeline(_FakeGstSink(sample))
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    with pytest.raises(RuntimeError, match="Unexpected GStreamer appsink buffer size 16"):
        runtime.sample_to_bgr(sample, width=3, height=2)


def test_pygobject_runtime_reports_map_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = _FakeGstBuffer(b"", map_success=False)
    sample = _FakeGstSample(buffer)
    pipeline = _FakeGstPipeline(_FakeGstSink(sample))
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    with pytest.raises(RuntimeError, match="Unable to map"):
        runtime.sample_to_bgr(sample, width=2, height=2)

    assert buffer.unmapped is False


def test_pygobject_runtime_stops_existing_pipeline_before_replacing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_pipeline = _FakeGstPipeline(_FakeGstSink(None))
    second_pipeline = _FakeGstPipeline(_FakeGstSink(None))
    fake_gst = _FakeRuntimeGst([first_pipeline, second_pipeline])
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    runtime.start("first ! appsink name=sink")
    runtime.start("second ! appsink name=sink")

    assert first_pipeline.states == [fake_gst.State.PLAYING, fake_gst.State.NULL]
    assert second_pipeline.states == [fake_gst.State.PLAYING]


def test_pygobject_runtime_rejects_pipeline_without_named_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = _FakeGstPipeline(None)
    fake_gst = _FakeRuntimeGst(pipeline)
    monkeypatch.setattr(
        "argus.vision.gstreamer_appsink.importlib.import_module",
        _fake_gi_import(fake_gst),
    )
    runtime = PyGObjectAppSinkRuntime()

    with pytest.raises(RuntimeError, match="sink named 'sink'"):
        runtime.start("fake ! appsink")

    assert pipeline.states == [fake_gst.State.NULL]


class _FakeElement:
    def __init__(self, properties: set[str]) -> None:
        self._properties = properties

    def find_property(self, name: str) -> object | None:
        if name in self._properties:
            return object()
        return None


class _FakeElementFactory:
    def __init__(
        self,
        *,
        properties: set[str] | None = None,
        create_error: Exception | None = None,
    ) -> None:
        self._properties = properties or set()
        self._create_error = create_error

    def create(self, name: str | None) -> _FakeElement:
        del name
        if self._create_error is not None:
            raise self._create_error
        return _FakeElement(self._properties)


class _FakeGstRegistry:
    def __init__(self, features: dict[str, _FakeElementFactory]) -> None:
        self._features = features

    def find_feature(
        self,
        name: str,
        element_factory_type: object,
    ) -> _FakeElementFactory | None:
        del element_factory_type
        return self._features.get(name)


def _available_appsink_features() -> dict[str, _FakeElementFactory]:
    return {
        "rtspsrc": _FakeElementFactory(),
        "rtph264depay": _FakeElementFactory(),
        "h264parse": _FakeElementFactory(),
        "queue": _FakeElementFactory(),
        "appsink": _FakeElementFactory(properties={"leaky-type"}),
        "videoconvert": _FakeElementFactory(),
        "nvv4l2decoder": _FakeElementFactory(properties={"disable-dpb"}),
        "nvvidconv": _FakeElementFactory(),
        "avdec_h264": _FakeElementFactory(),
        "videoscale": _FakeElementFactory(),
    }


class _FakeProbeGst:
    ElementFactory = object()

    def __init__(
        self,
        registry: _FakeGstRegistry,
        *,
        init_error: Exception | None = None,
        registry_error: Exception | None = None,
    ) -> None:
        self.init_args: list[object | None] = []
        self._init_error = init_error

        class Registry:
            @staticmethod
            def get() -> _FakeGstRegistry:
                if registry_error is not None:
                    raise registry_error
                return registry

        self.Registry = Registry

    def init(self, args: object | None) -> None:
        if self._init_error is not None:
            raise self._init_error
        self.init_args.append(args)


class _FakeGstBuffer:
    def __init__(self, payload: bytes, *, map_success: bool = True) -> None:
        self._payload = payload
        self._map_success = map_success
        self.map_flags: list[object] = []
        self.unmapped = False

    def map(self, flags: object) -> tuple[bool, object]:
        self.map_flags.append(flags)
        return self._map_success, SimpleNamespace(data=self._payload)

    def unmap(self, map_info: object) -> None:
        del map_info
        self.unmapped = True


class _FakeGstSample:
    def __init__(self, buffer: _FakeGstBuffer) -> None:
        self._buffer = buffer

    def get_buffer(self) -> _FakeGstBuffer:
        return self._buffer


class _FakeGstSink:
    def __init__(self, sample: _FakeGstSample | None) -> None:
        self._sample = sample
        self.emits: list[tuple[str, int]] = []

    def emit(self, signal_name: str, timeout_ns: int) -> _FakeGstSample | None:
        self.emits.append((signal_name, timeout_ns))
        return self._sample


class _FakeGstPipeline:
    def __init__(self, sink: _FakeGstSink | None) -> None:
        self._sink = sink
        self.states: list[str] = []

    def get_by_name(self, name: str) -> _FakeGstSink | None:
        if name == "sink":
            return self._sink
        return None

    def set_state(self, state: str) -> str:
        self.states.append(state)
        return "success"


class _FakeRuntimeGst:
    SECOND = 1_000_000_000

    class State:
        NULL = "null"
        PLAYING = "playing"

    class StateChangeReturn:
        FAILURE = "failure"

    class MapFlags:
        READ = "read"

    def __init__(self, pipeline: _FakeGstPipeline | list[_FakeGstPipeline]) -> None:
        if isinstance(pipeline, list):
            self._pipelines = pipeline
        else:
            self._pipelines = [pipeline]
        self.init_args: list[object | None] = []
        self.launches: list[str] = []

    def init(self, args: object | None) -> None:
        self.init_args.append(args)

    def parse_launch(self, launch: str) -> _FakeGstPipeline:
        self.launches.append(launch)
        index = min(len(self.launches) - 1, len(self._pipelines) - 1)
        return self._pipelines[index]


def _fake_gi_import(
    fake_gst: object,
    *,
    import_names: list[str] | None = None,
) -> Any:
    require_calls: list[tuple[str, str]] = []
    fake_gi = SimpleNamespace(
        require_calls=require_calls,
        require_version=lambda name, version: require_calls.append((name, version)),
    )
    fake_gst_app = object()

    def import_module(name: str, package: str | None = None) -> object:
        del package
        if import_names is not None:
            import_names.append(name)
        if name == "gi":
            return fake_gi
        if name == "gi.repository.Gst":
            return fake_gst
        if name == "gi.repository.GstApp":
            return fake_gst_app
        raise AssertionError(name)

    return import_module
