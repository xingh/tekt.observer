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


def test_operation_can_be_cancelled_from_a_new_manager(tmp_path):
    manager = OperationManager(tmp_path)
    op = manager.create("alpha", "run", [sys.executable, "-c", "import time; time.sleep(5)"])
    for _ in range(100):
        if manager.get(op["id"])["state"] == "running": break
        time.sleep(.01)
    cancelled = OperationManager(tmp_path).cancel(op["id"])
    assert cancelled["state"] == "cancelled"
    for _ in range(100):
        if op["id"] not in OperationManager._shared_processes: break
        time.sleep(.01)
    assert manager.get(op["id"])["state"] == "cancelled"
    with pytest.raises(PortfolioStateError, match="not active"):
        manager.cancel(op["id"])
