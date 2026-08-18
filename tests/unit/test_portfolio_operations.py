import sys
import time

import pytest

from portfolio_operations import OperationManager
from portfolio_state import PortfolioStateError


def test_operation_transitions_and_single_active_guard(tmp_path):
    manager = OperationManager(tmp_path)
    op = manager.create("alpha", "run", [sys.executable, "-c", "print('ok')"])
    with pytest.raises(PortfolioStateError, match="active"):
        manager.create("alpha", "run", [])
    for _ in range(100):
        current = manager.get(op["id"])
        if current["state"] in {"ready", "failed"}: break
        time.sleep(.01)
    assert current["state"] == "ready"
    assert current["log"].strip() == "ok"
