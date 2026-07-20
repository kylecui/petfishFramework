"""Minimal approval state machine for human-in-the-loop decisions."""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CONSUMED = "consumed"


@dataclass
class ApprovalRequest:
    request_id: str
    session_id: str
    tool_name: str
    args_hash: str
    policy_version: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    approver: str | None = None


class InMemoryApprovalStore:
    """Agent-scoped approval store, shared across all sessions of an Agent."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._lock = threading.Lock()

    def create(
        self,
        session_id: str,
        tool_name: str,
        args_hash: str,
        policy_version: str,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            tool_name=tool_name,
            args_hash=args_hash,
            policy_version=policy_version,
        )
        with self._lock:
            self._requests[request.request_id] = request
        return request

    def approve(self, request_id: str, approver: str = "") -> ApprovalRequest:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                raise KeyError(f"approval request {request_id} not found")
            if req.status != ApprovalStatus.PENDING:
                raise ValueError(
                    f"request {request_id} is {req.status.value}, cannot approve"
                )
            req.status = ApprovalStatus.APPROVED
            req.approver = approver
            return req

    def deny(self, request_id: str, reason: str = "") -> ApprovalRequest:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None:
                raise KeyError(f"approval request {request_id} not found")
            req.status = ApprovalStatus.DENIED
            return req

    def consume(self, request_id: str) -> bool:
        with self._lock:
            req = self._requests.get(request_id)
            if req is None or req.status != ApprovalStatus.APPROVED:
                return False
            req.status = ApprovalStatus.CONSUMED
            return True

    def get(self, request_id: str) -> ApprovalRequest | None:
        with self._lock:
            return self._requests.get(request_id)
