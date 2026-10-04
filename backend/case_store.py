from __future__ import annotations

import copy
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any


MAX_CASES = 128
_cases: OrderedDict[str, dict[str, Any]] = OrderedDict()


def store_case(case_id: str, payload: dict[str, Any]) -> None:
    record = copy.deepcopy(payload)
    record["case_id"] = case_id
    record.setdefault("stored_at", datetime.now(timezone.utc).isoformat())
    _cases[case_id] = record
    _cases.move_to_end(case_id)
    while len(_cases) > MAX_CASES:
        _cases.popitem(last=False)


def get_case(case_id: str) -> dict[str, Any] | None:
    record = _cases.get(case_id)
    if record is None:
        return None
    _cases.move_to_end(case_id)
    return copy.deepcopy(record)
