"""Core generic site fleet baseline."""

from argus.fleet.contracts import (
    EXCEPTION_ATTENTION_ORDER,
    AssignmentAssigneeType,
    FleetException,
    FleetExceptionKind,
    FleetIntegrityStatus,
    FleetLinkState,
    HeartbeatStatus,
    RotationGroup,
    RuntimeStatus,
    SiteAssignment,
    SiteGroup,
    SiteHierarchy,
    SiteHierarchyNode,
    SiteState,
)
from argus.fleet.service import FleetService

__all__ = [
    "EXCEPTION_ATTENTION_ORDER",
    "AssignmentAssigneeType",
    "FleetException",
    "FleetExceptionKind",
    "FleetIntegrityStatus",
    "FleetLinkState",
    "FleetService",
    "HeartbeatStatus",
    "RotationGroup",
    "RuntimeStatus",
    "SiteAssignment",
    "SiteGroup",
    "SiteHierarchy",
    "SiteHierarchyNode",
    "SiteState",
]
