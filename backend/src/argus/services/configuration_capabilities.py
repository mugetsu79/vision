from __future__ import annotations

from argus.api.contracts import (
    OperatorConfigFieldCapability,
    OperatorConfigKindCapability,
    OperatorConfigValueCapability,
)
from argus.models.enums import OperatorConfigProfileKind


def configuration_capabilities(
    *,
    nats_enabled: bool,
) -> list[OperatorConfigKindCapability]:
    push_support = "active" if nats_enabled else "requires_service"
    push_message = (
        "Push lifecycle requests require NATS supervisor acknowledgement."
        if nats_enabled
        else "Enable NATS supervisor push before binding push operations profiles."
    )
    return [
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.EVIDENCE_STORAGE,
            label="Evidence storage",
            runtime_support="active",
            operator_summary=(
                "Routes incident evidence to local, central, cloud, or local-first "
                "storage."
            ),
            secret_keys=["access_key", "secret_key"],
            fields=[
                OperatorConfigFieldCapability(
                    name="provider",
                    label="Provider",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(
                            value="local_filesystem",
                            support="active",
                        ),
                        OperatorConfigValueCapability(value="minio", support="active"),
                        OperatorConfigValueCapability(
                            value="s3_compatible",
                            support="active",
                        ),
                        OperatorConfigValueCapability(
                            value="local_first",
                            support="active",
                        ),
                    ],
                ),
                OperatorConfigFieldCapability(
                    name="storage_scope",
                    label="Storage scope",
                    support="active",
                ),
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.STREAM_DELIVERY,
            label="Transport profile",
            runtime_support="active",
            operator_summary=(
                "Selects the browser stream route and stream service prerequisites."
            ),
            fields=[
                OperatorConfigFieldCapability(
                    name="delivery_mode",
                    label="Transport mode",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(value="native", support="active"),
                        OperatorConfigValueCapability(value="webrtc", support="active"),
                        OperatorConfigValueCapability(value="hls", support="active"),
                        OperatorConfigValueCapability(value="mjpeg", support="active"),
                        OperatorConfigValueCapability(
                            value="transcode",
                            support="unsupported",
                            operator_message=(
                                "Use camera live rendition profiles for transcoding."
                            ),
                        ),
                    ],
                ),
                OperatorConfigFieldCapability(
                    name="public_base_url",
                    label="Public base URL",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="edge_override_url",
                    label="Edge override URL",
                    support="active",
                ),
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.RUNTIME_SELECTION,
            label="Runtime selection",
            runtime_support="active",
            operator_summary=(
                "Ranks runtime backends and model artifacts before worker start."
            ),
            fields=[
                OperatorConfigFieldCapability(
                    name="preferred_backend",
                    label="Preferred backend",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="artifact_preference",
                    label="Artifact preference",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="fallback_allowed",
                    label="Allow fallback",
                    support="active",
                ),
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.PRIVACY_POLICY,
            label="Privacy policy",
            runtime_support="active",
            operator_summary=(
                "Controls residency, plaintext plate posture, quota, and retention."
            ),
            fields=[
                OperatorConfigFieldCapability(
                    name="retention_days",
                    label="Retention days",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="storage_quota_bytes",
                    label="Storage quota bytes",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="plaintext_plate_storage",
                    label="Plaintext plate posture",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="residency",
                    label="Residency guardrail",
                    support="active",
                ),
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.LLM_PROVIDER,
            label="LLM provider",
            runtime_support="active",
            operator_summary=(
                "Provides model and credential settings for policy draft assistance."
            ),
            secret_keys=["api_key"],
            fields=[
                OperatorConfigFieldCapability(
                    name="provider",
                    label="Provider",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="model",
                    label="Model",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="base_url",
                    label="Base URL",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="api_key_required",
                    label="API key required",
                    support="active",
                ),
            ],
        ),
        OperatorConfigKindCapability(
            kind=OperatorConfigProfileKind.OPERATIONS_MODE,
            label="Operations mode",
            runtime_support="active",
            operator_summary=(
                "Controls worker lifecycle ownership, supervisor mode, and restart "
                "policy."
            ),
            fields=[
                OperatorConfigFieldCapability(
                    name="lifecycle_owner",
                    label="Lifecycle owner",
                    support="active",
                ),
                OperatorConfigFieldCapability(
                    name="supervisor_mode",
                    label="Supervisor mode",
                    support="active",
                    values=[
                        OperatorConfigValueCapability(
                            value="disabled",
                            support="active",
                        ),
                        OperatorConfigValueCapability(value="polling", support="active"),
                        OperatorConfigValueCapability(
                            value="push",
                            support=push_support,
                            requires=["nats"],
                            operator_message=push_message,
                        ),
                    ],
                ),
                OperatorConfigFieldCapability(
                    name="restart_policy",
                    label="Restart policy",
                    support="active",
                ),
            ],
        ),
    ]
