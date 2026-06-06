# ruff: noqa: I001
import importlib
import sys
from typing import Any

from argus.models.base import Base
from argus.models.enums import RoleEnum
from argus.models.tables import (
    APIKey,
    AuditLog,
    Camera,
    CameraVocabularySnapshot,
    CountEvent,
    CrossCameraThread,
    DeploymentCredentialEvent,
    DeploymentNode,
    DetectionRule,
    EdgeNode,
    EdgeNodeHardwareReport,
    EvidenceArtifact,
    EvidenceLedgerEntry,
    Incident,
    LocalFirstSyncAttempt,
    Model,
    ModelRuntimeArtifact,
    NodePairingSession,
    OperationsLifecycleRequest,
    OperatorConfigBinding,
    OperatorConfigProfile,
    OperatorConfigSecret,
    PrivacyManifestSnapshot,
    RuleEvent,
    RuntimePassportSnapshot,
    SceneContractSnapshot,
    Site,
    SupervisorNodeCredential,
    SupervisorServiceStatusReport,
    Tenant,
    TrackingEvent,
    User,
    WorkerAssignment,
    WorkerModelAdmissionReport,
    WorkerRuntimeReport,
)
if "argus.link.tables" not in sys.modules:
    from argus.link.tables import (
        LinkBudget,
        LinkConnection,
        LinkHealthProbe,
        LinkPassportSnapshot,
        LinkQueueItem,
        LinkTransferAttempt,
    )
if "argus.fleet.tables" not in sys.modules:
    from argus.fleet.tables import (
        FleetHierarchyNode,
        FleetRotationGroup,
        FleetSiteAssignment,
        FleetSiteGroup,
        FleetSiteState,
    )
if "argus.billing.tables" not in sys.modules:
    importlib.import_module("argus.billing.tables")
if "argus.support.tables" not in sys.modules:
    importlib.import_module("argus.support.tables")
if "argus.maritime.tables" not in sys.modules:
    importlib.import_module("argus.maritime.tables")

_LINK_TABLE_EXPORTS = {
    "LinkBudget",
    "LinkConnection",
    "LinkHealthProbe",
    "LinkPassportSnapshot",
    "LinkQueueItem",
    "LinkTransferAttempt",
}
_FLEET_TABLE_EXPORTS = {
    "FleetHierarchyNode",
    "FleetRotationGroup",
    "FleetSiteAssignment",
    "FleetSiteGroup",
    "FleetSiteState",
}
_BILLING_TABLE_EXPORTS = {
    "BillingAccount",
    "BillingExport",
    "BillingNode",
    "Entitlement",
    "InvoiceLineItem",
    "InvoiceRun",
    "PriceBook",
    "UsageMeter",
    "UsageRecord",
}
_SUPPORT_TABLE_EXPORTS = {
    "BreakGlassAccessRecord",
    "OnboardingCheckRun",
    "SupportBundle",
    "SupportSession",
    "SupportTunnel",
}


def __getattr__(name: str) -> Any:
    if name in _LINK_TABLE_EXPORTS:
        link_tables = importlib.import_module("argus.link.tables")
        value = getattr(link_tables, name)
        globals()[name] = value
        return value
    if name in _FLEET_TABLE_EXPORTS:
        fleet_tables = importlib.import_module("argus.fleet.tables")
        value = getattr(fleet_tables, name)
        globals()[name] = value
        return value
    if name in _BILLING_TABLE_EXPORTS:
        billing_tables = importlib.import_module("argus.billing.tables")
        value = getattr(billing_tables, name)
        globals()[name] = value
        return value
    if name in _SUPPORT_TABLE_EXPORTS:
        support_tables = importlib.import_module("argus.support.tables")
        value = getattr(support_tables, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "APIKey",
    "AuditLog",
    "Base",
    "BillingAccount",
    "BillingExport",
    "BillingNode",
    "BreakGlassAccessRecord",
    "Camera",
    "CameraVocabularySnapshot",
    "CountEvent",
    "CrossCameraThread",
    "DetectionRule",
    "DeploymentCredentialEvent",
    "DeploymentNode",
    "EdgeNode",
    "EdgeNodeHardwareReport",
    "Entitlement",
    "EvidenceArtifact",
    "EvidenceLedgerEntry",
    "FleetHierarchyNode",
    "FleetRotationGroup",
    "FleetSiteAssignment",
    "FleetSiteGroup",
    "FleetSiteState",
    "Incident",
    "InvoiceLineItem",
    "InvoiceRun",
    "LinkBudget",
    "LinkConnection",
    "LinkHealthProbe",
    "LinkPassportSnapshot",
    "LinkQueueItem",
    "LinkTransferAttempt",
    "LocalFirstSyncAttempt",
    "Model",
    "ModelRuntimeArtifact",
    "NodePairingSession",
    "OnboardingCheckRun",
    "OperationsLifecycleRequest",
    "OperatorConfigBinding",
    "OperatorConfigProfile",
    "OperatorConfigSecret",
    "PrivacyManifestSnapshot",
    "PriceBook",
    "RoleEnum",
    "RuleEvent",
    "RuntimePassportSnapshot",
    "SceneContractSnapshot",
    "Site",
    "SupervisorNodeCredential",
    "SupervisorServiceStatusReport",
    "SupportBundle",
    "SupportSession",
    "SupportTunnel",
    "Tenant",
    "TrackingEvent",
    "UsageMeter",
    "UsageRecord",
    "User",
    "WorkerAssignment",
    "WorkerModelAdmissionReport",
    "WorkerRuntimeReport",
]
