from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import BrowserDeliverySettings, SourceCapability
from argus.models.enums import ProcessingMode
from argus.services.app import _build_source_aware_browser_delivery


def _profiles_by_id(settings: BrowserDeliverySettings) -> dict[str, dict[str, object]]:
    return {str(profile["id"]): profile for profile in settings.profiles}


def test_central_browser_delivery_labels_preview_scope() -> None:
    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="720p10"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": False, "blur_plates": False},
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
    )

    profiles = _profiles_by_id(settings)

    assert settings.default_profile == "720p10"
    assert profiles["native"]["label"] == "Native camera"
    assert profiles["annotated"]["label"] == "Annotated"
    assert profiles["720p10"]["label"] == "720p10 viewer preview"
    assert profiles["720p10"]["description"] == (
        "Reduces master-to-browser bandwidth only; central inference still ingests "
        "the native camera stream."
    )


def test_edge_browser_delivery_labels_edge_bandwidth_scope() -> None:
    edge_node_id = uuid4()

    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="720p10"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": False, "blur_plates": False},
        processing_mode=ProcessingMode.EDGE,
        edge_node_id=edge_node_id,
    )

    profiles = _profiles_by_id(settings)

    assert profiles["native"]["label"] == "Native edge passthrough"
    assert profiles["annotated"]["label"] == "Annotated edge stream"
    assert profiles["720p10"]["label"] == "720p10 edge bandwidth saver"
    assert profiles["720p10"]["description"] == (
        "Downscaled on the edge node before remote browser delivery."
    )


def test_native_with_privacy_resolves_to_processed_profile() -> None:
    settings = _build_source_aware_browser_delivery(
        requested=BrowserDeliverySettings(default_profile="native"),
        source_capability=SourceCapability(width=1920, height=1080, fps=25),
        privacy={"blur_faces": True, "blur_plates": False},
        processing_mode=ProcessingMode.CENTRAL,
        edge_node_id=None,
    )

    assert settings.default_profile == "annotated"
    assert settings.native_status.available is False
    assert settings.native_status.reason == "privacy_filtering_required"
