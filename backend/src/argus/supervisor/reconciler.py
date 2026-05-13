from __future__ import annotations

from typing import Protocol
from uuid import UUID

from argus.api.contracts import OperationsLifecycleRequestResponse
from argus.models.enums import (
    ModelAdmissionStatus,
    OperationsLifecycleAction,
    OperationsLifecycleStatus,
)
from argus.supervisor.process_adapter import WorkerProcessAdapter, WorkerProcessResult

_START_ACTIONS = {OperationsLifecycleAction.START, OperationsLifecycleAction.RESTART}
_ADMITTED_STATUSES = {
    ModelAdmissionStatus.RECOMMENDED,
    ModelAdmissionStatus.SUPPORTED,
    ModelAdmissionStatus.DEGRADED,
}


class SupervisorOperationsClient(Protocol):
    async def poll_lifecycle_requests(
        self,
        *,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
        limit: int,
    ) -> list[OperationsLifecycleRequestResponse]: ...

    async def claim_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None,
    ) -> OperationsLifecycleRequestResponse: ...

    async def evaluate_model_admission_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
    ): ...

    async def complete_lifecycle_request(
        self,
        *,
        tenant_id: UUID,
        request_id: UUID,
        supervisor_id: str,
        status: OperationsLifecycleStatus,
        admission_report_id: UUID | None = None,
        error: str | None = None,
    ) -> OperationsLifecycleRequestResponse: ...

    async def record_runtime_report_for_request(
        self,
        *,
        tenant_id: UUID,
        request: OperationsLifecycleRequestResponse,
        runtime_state: str,
        last_error: str | None = None,
    ) -> None: ...


class SupervisorReconciler:
    def __init__(
        self,
        *,
        operations: SupervisorOperationsClient,
        process_adapter: WorkerProcessAdapter,
        tenant_id: UUID,
        supervisor_id: str,
        edge_node_id: UUID | None = None,
        limit: int = 10,
    ) -> None:
        self.operations = operations
        self.process_adapter = process_adapter
        self.tenant_id = tenant_id
        self.supervisor_id = supervisor_id
        self.edge_node_id = edge_node_id
        self.limit = limit

    async def reconcile_once(self) -> int:
        requests = await self.operations.poll_lifecycle_requests(
            tenant_id=self.tenant_id,
            supervisor_id=self.supervisor_id,
            edge_node_id=self.edge_node_id,
            limit=self.limit,
        )
        processed = 0
        for request in requests:
            claimed = await self.operations.claim_lifecycle_request(
                tenant_id=self.tenant_id,
                request_id=request.id,
                supervisor_id=self.supervisor_id,
                edge_node_id=self.edge_node_id,
            )
            await self._process_claimed_request(claimed)
            processed += 1
        return processed

    async def _process_claimed_request(
        self,
        request: OperationsLifecycleRequestResponse,
    ) -> None:
        admission_report_id = None
        if request.action in _START_ACTIONS:
            admission = await self.operations.evaluate_model_admission_for_request(
                tenant_id=self.tenant_id,
                request=request,
            )
            admission_report_id = admission.id
            if admission.status not in _ADMITTED_STATUSES:
                await self.operations.complete_lifecycle_request(
                    tenant_id=self.tenant_id,
                    request_id=request.id,
                    supervisor_id=self.supervisor_id,
                    status=OperationsLifecycleStatus.FAILED,
                    admission_report_id=admission_report_id,
                    error=f"model admission {admission.status.value}: {admission.rationale}",
                )
                return

        result = await self._execute(request)
        await self.operations.record_runtime_report_for_request(
            tenant_id=self.tenant_id,
            request=request,
            runtime_state=result.runtime_state,
            last_error=result.last_error,
        )
        await self.operations.complete_lifecycle_request(
            tenant_id=self.tenant_id,
            request_id=request.id,
            supervisor_id=self.supervisor_id,
            status=(
                OperationsLifecycleStatus.FAILED
                if result.last_error
                else OperationsLifecycleStatus.COMPLETED
            ),
            admission_report_id=admission_report_id,
            error=result.last_error,
        )

    async def _execute(
        self,
        request: OperationsLifecycleRequestResponse,
    ) -> WorkerProcessResult:
        if request.action is OperationsLifecycleAction.START:
            return await self.process_adapter.start(request.camera_id)
        if request.action is OperationsLifecycleAction.STOP:
            return await self.process_adapter.stop(request.camera_id)
        if request.action is OperationsLifecycleAction.RESTART:
            return await self.process_adapter.restart(request.camera_id)
        if request.action is OperationsLifecycleAction.DRAIN:
            return await self.process_adapter.drain(request.camera_id)
        return WorkerProcessResult(
            runtime_state="error",
            last_error=f"Unsupported lifecycle action {request.action!s}.",
        )
