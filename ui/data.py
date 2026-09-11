"""Cached views over the API. Nothing here imports `core` - the UI reaches
the domain only through HTTP, so the solver cannot be pulled into Streamlit's
rerun loop and `data/` keeps exactly one writer.

Streamlit reruns this whole script on every widget change, so every call has
to be cached or gated behind a button. An uncached call here means a solve
per keystroke.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import streamlit as st

from . import client
from .client import ApiError, Unreachable   # noqa: F401  (re-exported)


@st.cache_data(ttl=60, show_spinner=False)
def units() -> List[Dict]:
    return client.units()


@st.cache_data(ttl=900, show_spinner=False)
def fleet_status() -> Dict:
    return client.unit_status()


@st.cache_data(ttl=3600, show_spinner=False)
def unit_fields() -> List[Dict]:
    return client.unit_fields()


# --- registry edits: every one of them busts the units cache -------------
def create_unit(user: str, name: str, params: Dict, apps: List[str],
                note: str = "") -> Dict:
    out = client.create_unit(user, name, params, apps, note)
    units.clear()
    return out


def create_variant(user: str, base: str, changes: Dict,
                   new_name: str | None = None) -> Dict:
    out = client.create_variant(user, base, changes, new_name)
    units.clear()
    return out


def delete_unit(user: str, name: str) -> Dict:
    out = client.delete_unit(user, name)
    units.clear()
    return out


def unit_by_name(name: str) -> Dict | None:
    return next((u for u in units() if u["name"] == name), None)


@st.cache_data(show_spinner=False, max_entries=32)
def _simulate(req_json: str, user: str) -> Dict[str, Any]:
    """Keyed on the request itself: same inputs, same answer, no second call.
    The argument is a JSON string because the cache key must be hashable."""
    return client.simulate(json.loads(req_json), user)


def simulate(req: Dict, user: str) -> Dict[str, Any]:
    return _simulate(json.dumps(req, sort_keys=True), user)


def clear_caches() -> None:
    units.clear()
    fleet_status.clear()
    _simulate.clear()


# --- cases: never cached, they change under us ---------------------------
def list_cases(user: str) -> List[Dict]:
    return client.list_cases(user)


def save_case(user: str, name: str, req: Dict) -> Dict:
    return client.save_case(user, name, req)


def load_case(user: str, case_id: str) -> Dict:
    return client.get_case(user, case_id)


def delete_case(user: str, case_id: str) -> None:
    client.delete_case(user, case_id)
