from __future__ import annotations

import pytest

from argus.billing.service import BillingService


@pytest.fixture
def billing_service() -> BillingService:
    return BillingService()
