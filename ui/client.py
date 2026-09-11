"""HTTP client for the API. The ONLY way the UI reaches the domain.

The UI process must not import `core` and must not touch `data/` - that
separation is the point of the split, and it is what stops two writers from
appearing on the same files. This module is the whole boundary.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx

BASE = os.getenv("LIFTSIM_API", "https://lift-simulator-backend.up.railway.app")
TIMEOUT = httpx.Timeout(connect=2.0, read=60.0, write=10.0, pool=2.0)


class Unreachable(RuntimeError):
    """The API is not answering. Distinct from a rejected request: one means
    the backend is down, the other means the inputs were wrong."""


class ApiError(RuntimeError):
    """The API answered, and said no. `message` is already readable."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def _explain(r: httpx.Response) -> str:
    """422 bodies are a list of field errors - show the field, not 'failed'."""
    try:
        body = r.json()
    except ValueError:
        return f"HTTP {r.status_code}"
    d = body.get("detail", body)
    if isinstance(d, str):
        return d
    if isinstance(d, list):
        out = []
        for e in d:
            loc = ".".join(str(x) for x in e.get("loc", []) if x != "body")
            out.append(f"{loc}: {e.get('msg', '')}".strip(": "))
        return "; ".join(out) or f"HTTP {r.status_code}"
    return f"HTTP {r.status_code}"


def _call(method: str, path: str, *, user: str | None = None,
          json: Any = None, params: Dict | None = None) -> Any:
    headers = {"X-User": user} if user else {}
    try:
        with httpx.Client(base_url=BASE, timeout=TIMEOUT) as c:
            r = c.request(method, path, json=json, params=params, headers=headers)
    except httpx.HTTPError as exc:
        raise Unreachable(str(exc)) from exc
    if r.status_code >= 400:
        raise ApiError(r.status_code, _explain(r))
    return None if r.status_code == 204 else r.json()


# --- probes --------------------------------------------------------------
def health() -> Dict:
    return _call("GET", "/health")


def boot() -> Dict:
    """Warm-up progress. Public on purpose: the sign-in page renders it
    before anybody has signed in."""
    return _call("GET", "/public/boot")


# --- domain --------------------------------------------------------------
def units(include_deleted: bool = False) -> List[Dict]:
    return _call("GET", "/units",
                 params={"include_deleted": str(include_deleted).lower()})


def unit_status() -> Dict:
    return _call("GET", "/units/status")


def unit_fields() -> List[Dict]:
    return _call("GET", "/units/fields")


def create_unit(user: str, name: str, params: Dict, applications: List[str],
                note: str = "") -> Dict:
    return _call("POST", "/units", user=user,
                 json={"name": name, "params": params,
                       "applications": applications, "note": note})


def create_variant(user: str, base_name: str, changes: Dict,
                   new_name: str | None = None) -> Dict:
    """Edit is always a NEW unit. A catalogue unit is referenced by saved
    cases, so overwriting one would make old results unreproducible - the API
    refuses it, and this is the only edit path the UI offers."""
    return _call("POST", "/units/variant", user=user,
                 json={"base_name": base_name, "new_name": new_name,
                       "changes": changes})


def delete_unit(user: str, name: str) -> Dict:
    """Soft delete: state = 0. The record stays, so a case that named this
    unit still resolves it."""
    return _call("DELETE", "/units", user=user, params={"name": name})


def simulate(req: Dict, user: str) -> Dict:
    return _call("POST", "/simulate", user=user, json=req)


def list_cases(user: str) -> List[Dict]:
    return _call("GET", "/cases", user=user)


def save_case(user: str, name: str, inputs: Dict) -> Dict:
    return _call("POST", "/cases", user=user,
                 json={"name": name, "inputs": inputs})


def get_case(user: str, case_id: str) -> Dict:
    return _call("GET", f"/cases/{case_id}", user=user)


def delete_case(user: str, case_id: str) -> None:
    _call("DELETE", f"/cases/{case_id}", user=user)
