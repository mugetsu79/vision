from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.billing.contracts import (
    BillingAccountRecord,
    BillingNodeRecord,
    InvoiceRunRecord,
    UsageRecord,
)
from argus.billing.service import BillingService
from argus.compat import UTC
from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.models.enums import (
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentReviewStatus,
)
from argus.models.tables import (
    EvidenceArtifact,
    EvidenceLedgerEntry,
    Incident,
    PrivacyManifestSnapshot,
    RuntimePassportSnapshot,
    SceneContractSnapshot,
    TrackingEvent,
)


@dataclass(frozen=True, slots=True)
class SmokeFixtureRequest:
    tenant_id: UUID
    site_id: UUID
    camera_id: UUID
    smoke_run_id: str
    occurred_at: datetime
    evidence_root: Path


@dataclass(frozen=True, slots=True)
class SmokeFixtureResult:
    incident_id: UUID
    artifact_id: UUID
    artifact_path: Path
    artifact_sha256: str
    history_class_name: str
    tracking_event_count: int
    usage_record_count: int
    billing_node_id: UUID
    billing_account_id: UUID
    invoice_run_id: UUID


async def seed_smoke_fixture(
    session_factory: async_sessionmaker[AsyncSession],
    request: SmokeFixtureRequest,
    *,
    billing_service: BillingService | None = None,
) -> SmokeFixtureResult:
    incident_id = _fixture_uuid(request, "incident")
    artifact_id = _fixture_uuid(request, "artifact")
    scene_snapshot_id = _fixture_uuid(request, "scene-contract")
    privacy_snapshot_id = _fixture_uuid(request, "privacy-manifest")
    passport_snapshot_id = _fixture_uuid(request, "runtime-passport")
    ledger_entry_id = _fixture_uuid(request, "ledger-entry-1")
    artifact_dir = request.evidence_root / request.smoke_run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{artifact_id}.txt"
    artifact_object_key = f"{request.smoke_run_id}/{artifact_path.name}"
    artifact_payload = (
        "Vezor whole-product smoke evidence\n"
        f"smoke_run_id={request.smoke_run_id}\n"
        f"camera_id={request.camera_id}\n"
        "class_name=person\n"
    ).encode()
    artifact_path.write_bytes(artifact_payload)
    artifact_sha256 = _hash_payload(artifact_payload)

    async with session_factory() as session:
        await _upsert_tracking_event(session, request)
        scene_hash = _hash_payload(f"scene:{request.smoke_run_id}".encode())
        privacy_hash = _hash_payload(f"privacy:{request.smoke_run_id}".encode())
        passport_hash = _hash_payload(f"runtime:{request.smoke_run_id}".encode())
        await _upsert_scene_contract(session, request, scene_snapshot_id, scene_hash)
        await _upsert_privacy_manifest(session, request, privacy_snapshot_id, privacy_hash)
        await _upsert_runtime_passport(
            session,
            request,
            passport_snapshot_id,
            passport_hash,
            privacy_hash,
            incident_id=None,
        )
        await _upsert_incident(
            session,
            request,
            incident_id,
            scene_snapshot_id,
            scene_hash,
            privacy_snapshot_id,
            privacy_hash,
            passport_snapshot_id,
            passport_hash,
            len(artifact_payload),
        )
        await session.flush()
        await _link_runtime_passport(session, passport_snapshot_id, incident_id)
        await _upsert_artifact(
            session,
            request,
            artifact_id,
            incident_id,
            artifact_object_key,
            artifact_sha256,
            len(artifact_payload),
            scene_hash,
            privacy_hash,
        )
        await _upsert_ledger(session, request, ledger_entry_id, incident_id, artifact_id)
        await session.commit()

    billing = billing_service or BillingService(session_factory)
    billing_result = await _seed_billing(
        billing,
        request=request,
        incident_id=incident_id,
        artifact_id=artifact_id,
    )
    return SmokeFixtureResult(
        incident_id=incident_id,
        artifact_id=artifact_id,
        artifact_path=artifact_path,
        artifact_sha256=artifact_sha256,
        history_class_name="person",
        tracking_event_count=1,
        usage_record_count=billing_result.usage_record_count,
        billing_node_id=billing_result.node.id,
        billing_account_id=billing_result.account.id,
        invoice_run_id=billing_result.invoice.id,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed deterministic whole-product smoke data.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--camera-id", required=True)
    parser.add_argument("--smoke-run-id", required=True)
    parser.add_argument("--occurred-at", required=True)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=Path("/var/lib/vezor/evidence"),
    )
    return parser.parse_args(argv)


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    database = DatabaseManager(Settings())
    try:
        result = await seed_smoke_fixture(
            database.session_factory,
            SmokeFixtureRequest(
                tenant_id=UUID(args.tenant_id),
                site_id=UUID(args.site_id),
                camera_id=UUID(args.camera_id),
                smoke_run_id=args.smoke_run_id,
                occurred_at=_parse_datetime(args.occurred_at),
                evidence_root=args.evidence_root,
            ),
        )
    finally:
        await database.dispose()
    print(
        json.dumps(
            {
                "incident_id": str(result.incident_id),
                "artifact_id": str(result.artifact_id),
                "artifact_sha256": result.artifact_sha256,
                "billing_node_id": str(result.billing_node_id),
                "billing_account_id": str(result.billing_account_id),
                "invoice_run_id": str(result.invoice_run_id),
                "usage_record_count": result.usage_record_count,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


def _fixture_uuid(request: SmokeFixtureRequest, suffix: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        "vezor:whole-product-smoke:"
        f"{request.tenant_id}:{request.camera_id}:{request.smoke_run_id}:{suffix}",
    )


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _entry_hash(*, previous: str | None, payload: dict[str, object]) -> str:
    base = f"{previous or ''}:{json.dumps(payload, sort_keys=True)}".encode()
    return hashlib.sha256(base).hexdigest()


async def _upsert_tracking_event(session: AsyncSession, request: SmokeFixtureRequest) -> None:
    existing = await session.execute(
        select(TrackingEvent)
        .where(TrackingEvent.camera_id == request.camera_id)
        .where(TrackingEvent.ts == request.occurred_at)
        .where(TrackingEvent.track_id == 2609)
    )
    row = existing.scalars().first()
    attrs = {"smoke_run_id": request.smoke_run_id, "source": "whole_product_smoke_fixture"}
    if row is None:
        session.add(
            TrackingEvent(
                id=_fixture_uuid(request, "tracking-event"),
                ts=request.occurred_at,
                camera_id=request.camera_id,
                class_name="person",
                track_id=2609,
                confidence=0.93,
                speed_kph=None,
                direction_deg=None,
                zone_id="office-entry",
                attributes=attrs,
                bbox={"x": 0.42, "y": 0.22, "width": 0.16, "height": 0.48},
            )
        )
        return
    row.attributes = attrs
    row.class_name = "person"
    row.confidence = 0.93
    row.bbox = {"x": 0.42, "y": 0.22, "width": 0.16, "height": 0.48}


async def _upsert_scene_contract(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    snapshot_id: UUID,
    scene_hash: str,
) -> None:
    payload = {
        "schema": "whole_product_smoke.scene_contract.v1",
        "smoke_run_id": request.smoke_run_id,
        "site_id": str(request.site_id),
        "camera_id": str(request.camera_id),
        "zones": [{"id": "office-entry", "label": "Office entry"}],
    }
    row = await session.get(SceneContractSnapshot, snapshot_id)
    if row is None:
        session.add(
            SceneContractSnapshot(
                id=snapshot_id,
                tenant_id=request.tenant_id,
                camera_id=request.camera_id,
                schema_version=1,
                contract_hash=scene_hash,
                contract=payload,
            )
        )
        return
    row.contract_hash = scene_hash
    row.contract = payload


async def _upsert_privacy_manifest(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    snapshot_id: UUID,
    privacy_hash: str,
) -> None:
    payload = {
        "schema": "whole_product_smoke.privacy_manifest.v1",
        "smoke_run_id": request.smoke_run_id,
        "retention": {"mode": "smoke_fixture", "days": 1},
        "redaction": {"faces": "not_applicable", "plates": "not_applicable"},
    }
    row = await session.get(PrivacyManifestSnapshot, snapshot_id)
    if row is None:
        session.add(
            PrivacyManifestSnapshot(
                id=snapshot_id,
                tenant_id=request.tenant_id,
                camera_id=request.camera_id,
                schema_version=1,
                manifest_hash=privacy_hash,
                manifest=payload,
            )
        )
        return
    row.manifest_hash = privacy_hash
    row.manifest = payload


async def _upsert_runtime_passport(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    snapshot_id: UUID,
    passport_hash: str,
    privacy_hash: str,
    incident_id: UUID | None,
) -> None:
    payload = {
        "schema": "whole_product_smoke.runtime_passport.v1",
        "smoke_run_id": request.smoke_run_id,
        "selected_backend": "deterministic_fixture",
        "model_name": "YOLO26n COCO",
        "privacy_manifest_hash": privacy_hash,
    }
    row = await session.get(RuntimePassportSnapshot, snapshot_id)
    if row is None:
        session.add(
            RuntimePassportSnapshot(
                id=snapshot_id,
                tenant_id=request.tenant_id,
                camera_id=request.camera_id,
                incident_id=incident_id,
                schema_version=1,
                passport_hash=passport_hash,
                passport=payload,
            )
        )
        return
    row.incident_id = incident_id
    row.passport_hash = passport_hash
    row.passport = payload


async def _link_runtime_passport(
    session: AsyncSession,
    snapshot_id: UUID,
    incident_id: UUID,
) -> None:
    row = await session.get(RuntimePassportSnapshot, snapshot_id)
    if row is not None:
        row.incident_id = incident_id


async def _upsert_incident(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    incident_id: UUID,
    scene_snapshot_id: UUID,
    scene_hash: str,
    privacy_snapshot_id: UUID,
    privacy_hash: str,
    passport_snapshot_id: UUID,
    passport_hash: str,
    storage_bytes: int,
) -> None:
    payload = {
        "smoke_run_id": request.smoke_run_id,
        "source": "whole_product_smoke_fixture",
        "class_name": "person",
        "track_id": 2609,
        "zone_id": "office-entry",
        "trigger_rule": {
            "id": "whole-product-smoke-person",
            "name": "Whole-product smoke person fixture",
        },
    }
    row = await session.get(Incident, incident_id)
    if row is None:
        session.add(
            Incident(
                id=incident_id,
                camera_id=request.camera_id,
                ts=request.occurred_at,
                type="whole_product_smoke",
                payload=payload,
                snapshot_url=None,
                clip_url=None,
                storage_bytes=storage_bytes,
                scene_contract_snapshot_id=scene_snapshot_id,
                scene_contract_hash=scene_hash,
                privacy_manifest_snapshot_id=privacy_snapshot_id,
                privacy_manifest_hash=privacy_hash,
                runtime_passport_snapshot_id=passport_snapshot_id,
                runtime_passport_hash=passport_hash,
                recording_policy={
                    "mode": "event_clip",
                    "pre_seconds": 4,
                    "post_seconds": 8,
                    "fps": 10,
                    "max_duration_seconds": 15,
                    "storage_profile": "central",
                    "snapshot_enabled": False,
                },
                review_status=IncidentReviewStatus.PENDING,
            )
        )
        return
    row.ts = request.occurred_at
    row.payload = payload
    row.storage_bytes = storage_bytes
    row.scene_contract_snapshot_id = scene_snapshot_id
    row.scene_contract_hash = scene_hash
    row.privacy_manifest_snapshot_id = privacy_snapshot_id
    row.privacy_manifest_hash = privacy_hash
    row.runtime_passport_snapshot_id = passport_snapshot_id
    row.runtime_passport_hash = passport_hash
    row.recording_policy = {
        "mode": "event_clip",
        "pre_seconds": 4,
        "post_seconds": 8,
        "fps": 10,
        "max_duration_seconds": 15,
        "storage_profile": "central",
        "snapshot_enabled": False,
    }


async def _upsert_artifact(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    artifact_id: UUID,
    incident_id: UUID,
    object_key: str,
    artifact_sha256: str,
    size_bytes: int,
    scene_hash: str,
    privacy_hash: str,
) -> None:
    row = await session.get(EvidenceArtifact, artifact_id)
    if row is None:
        session.add(
            EvidenceArtifact(
                id=artifact_id,
                incident_id=incident_id,
                camera_id=request.camera_id,
                kind=EvidenceArtifactKind.MANIFEST_EXPORT,
                status=EvidenceArtifactStatus.AVAILABLE,
                storage_provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
                storage_scope=EvidenceStorageScope.CENTRAL,
                bucket=None,
                object_key=object_key,
                content_type="text/plain; charset=utf-8",
                sha256=artifact_sha256,
                size_bytes=size_bytes,
                clip_started_at=None,
                triggered_at=request.occurred_at,
                clip_ended_at=None,
                duration_seconds=None,
                fps=None,
                scene_contract_hash=scene_hash,
                privacy_manifest_hash=privacy_hash,
            )
        )
        return
    row.object_key = object_key
    row.sha256 = artifact_sha256
    row.size_bytes = size_bytes
    row.triggered_at = request.occurred_at
    row.scene_contract_hash = scene_hash
    row.privacy_manifest_hash = privacy_hash


async def _upsert_ledger(
    session: AsyncSession,
    request: SmokeFixtureRequest,
    ledger_entry_id: UUID,
    incident_id: UUID,
    artifact_id: UUID,
) -> None:
    payload = {
        "smoke_run_id": request.smoke_run_id,
        "source": "whole_product_smoke_fixture",
        "artifact_id": str(artifact_id),
    }
    row = await session.get(EvidenceLedgerEntry, ledger_entry_id)
    entry_hash = _entry_hash(previous=None, payload=payload)
    if row is None:
        session.add(
            EvidenceLedgerEntry(
                id=ledger_entry_id,
                tenant_id=request.tenant_id,
                incident_id=incident_id,
                camera_id=request.camera_id,
                sequence=1,
                action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
                actor_type="system",
                actor_subject="whole-product-smoke-fixture",
                occurred_at=request.occurred_at,
                payload=payload,
                previous_entry_hash=None,
                entry_hash=entry_hash,
            )
        )
        return
    row.payload = payload
    row.entry_hash = entry_hash
    row.occurred_at = request.occurred_at


@dataclass(frozen=True, slots=True)
class _BillingFixtureResult:
    node: BillingNodeRecord
    account: BillingAccountRecord
    invoice: InvoiceRunRecord
    usage_record_count: int


async def _seed_billing(
    billing: BillingService,
    *,
    request: SmokeFixtureRequest,
    incident_id: UUID,
    artifact_id: UUID,
) -> _BillingFixtureResult:
    node = await _billing_node(billing, request)
    account = await _billing_account(billing, request, node)
    await _billing_entitlement(billing, request, account)
    await _billing_price_book(billing, request)
    usage_records = await _billing_usage_records(
        billing,
        request=request,
        account=account,
        node=node,
        incident_id=incident_id,
        artifact_id=artifact_id,
    )
    invoice = await _billing_invoice(billing, request, account)
    return _BillingFixtureResult(
        node=node,
        account=account,
        invoice=invoice,
        usage_record_count=len(usage_records),
    )


async def _billing_node(
    billing: BillingService,
    request: SmokeFixtureRequest,
) -> BillingNodeRecord:
    existing = _matching_smoke_record(
        await billing.alist_nodes(tenant_id=request.tenant_id),
        request,
    )
    if existing is not None:
        return existing
    return await billing.acreate_node(
        tenant_id=request.tenant_id,
        label=f"Smoke Office Node {request.smoke_run_id}",
        kind="site",
        attributes={"smoke_run_id": request.smoke_run_id, "site_id": str(request.site_id)},
    )


async def _billing_account(
    billing: BillingService,
    request: SmokeFixtureRequest,
    node: BillingNodeRecord,
) -> BillingAccountRecord:
    existing = _matching_smoke_record(
        await billing.alist_accounts(tenant_id=request.tenant_id),
        request,
    )
    if existing is not None:
        return existing
    return await billing.acreate_account(
        tenant_id=request.tenant_id,
        name=f"Smoke Account {request.smoke_run_id}",
        node_ids=[node.id],
        attributes={"smoke_run_id": request.smoke_run_id},
    )


async def _billing_entitlement(
    billing: BillingService,
    request: SmokeFixtureRequest,
    account: BillingAccountRecord,
) -> None:
    entitlements = await billing.alist_entitlements(
        tenant_id=request.tenant_id,
        account_id=account.id,
    )
    if _matching_smoke_record(entitlements, request) is not None:
        return
    await billing.agrant_entitlement(
        tenant_id=request.tenant_id,
        account_id=account.id,
        feature_key="whole_product_smoke",
        effective_from=request.occurred_at.date(),
        attributes={"smoke_run_id": request.smoke_run_id},
    )


async def _billing_price_book(billing: BillingService, request: SmokeFixtureRequest) -> None:
    meter_prices = {
        "evidence_pack_export": Decimal("5.00"),
        "managed_edge_node": Decimal("25.00"),
    }
    for price_book in await billing.alist_price_books(tenant_id=request.tenant_id):
        if (
            price_book.currency == "USD"
            and price_book.effective_from == request.occurred_at.date()
            and all(meter in price_book.meter_prices for meter in meter_prices)
        ):
            return
    await billing.acreate_price_book(
        tenant_id=request.tenant_id,
        currency="USD",
        effective_from=request.occurred_at.date(),
        meter_prices=meter_prices,
    )


async def _billing_usage_records(
    billing: BillingService,
    *,
    request: SmokeFixtureRequest,
    account: BillingAccountRecord,
    node: BillingNodeRecord,
    incident_id: UUID,
    artifact_id: UUID,
) -> list[UsageRecord]:
    existing = [
        usage
        for usage in await billing.alist_usage(tenant_id=request.tenant_id)
        if usage.metadata.get("smoke_run_id") == request.smoke_run_id
        and usage.meter_key in {"evidence_pack_export", "managed_edge_node"}
    ]
    if {usage.meter_key for usage in existing} == {"evidence_pack_export", "managed_edge_node"}:
        return sorted(existing, key=lambda usage: usage.meter_key)

    records = list(existing)
    existing_meters = {usage.meter_key for usage in existing}
    if "evidence_pack_export" not in existing_meters:
        records.append(
            await billing.arecord_usage(
                tenant_id=request.tenant_id,
                meter_key="evidence_pack_export",
                quantity=Decimal("1"),
                account_id=account.id,
                node_id=node.id,
                source_object_type="smoke_evidence_artifact",
                source_object_id=artifact_id,
                occurred_on=request.occurred_at.date(),
                metadata={"smoke_run_id": request.smoke_run_id, "incident_id": str(incident_id)},
            )
        )
    if "managed_edge_node" not in existing_meters:
        records.append(
            await billing.arecord_usage(
                tenant_id=request.tenant_id,
                meter_key="managed_edge_node",
                quantity=Decimal("1"),
                account_id=account.id,
                node_id=node.id,
                source_object_type="smoke_site",
                source_object_id=request.site_id,
                occurred_on=request.occurred_at.date(),
                metadata={"smoke_run_id": request.smoke_run_id},
            )
        )
    return sorted(records, key=lambda usage: usage.meter_key)


async def _billing_invoice(
    billing: BillingService,
    request: SmokeFixtureRequest,
    account: BillingAccountRecord,
) -> InvoiceRunRecord:
    period_start = request.occurred_at.date()
    period_end = period_start + timedelta(days=1)
    for invoice in await billing.alist_invoice_runs(tenant_id=request.tenant_id):
        if (
            invoice.account_id == account.id
            and invoice.period_start == period_start
            and invoice.period_end == period_end
        ):
            return invoice
    return await billing.arun_invoice(
        tenant_id=request.tenant_id,
        account_id=account.id,
        period_start=period_start,
        period_end=period_end,
    )


def _matching_smoke_record(records: Sequence[Any], request: SmokeFixtureRequest) -> Any | None:
    for record in records:
        attributes = getattr(record, "attributes", {})
        if isinstance(attributes, dict) and attributes.get("smoke_run_id") == request.smoke_run_id:
            return record
    return None


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


if __name__ == "__main__":
    main()
