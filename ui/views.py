"""The two pages.

Streamlit reruns this whole file on every interaction, so nothing here holds
state of its own: it lives in st.session_state, or in the caches in data.py.
The request is built with the API's own Pydantic models - one definition of
the contract, so the two sides cannot drift.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

import streamlit as st
from pydantic import ValidationError

from api.schemas import APPLICATIONS, ClientInputs, SafelinkInputs, SimRequest  # pure pydantic
from . import auth, charts, chrome, data, theme as T

FIG_DIR = Path(__file__).resolve().parent.parent / "web" / "figures"
PRIORITIES = ["Release to atm", "Release to SS", "Release to HP",
              "Add from HP", "Add from LP", "Pump to HP"]
PROFILES = ["Safelink formula", "Constant"]     # only what is implemented


# ===================================================================== rail
def _sequence_editor() -> List[Dict]:
    rows = st.session_state.setdefault("seq", [
        {"enabled": True, "depth_m": 0.0, "stroke_m": 2.25, "mode": "SZ"},
        {"enabled": True, "depth_m": 1276.0, "stroke_m": 2.25, "mode": "SS"},
        {"enabled": False, "depth_m": 0.0, "stroke_m": 0.0, "mode": "SZ"},
    ])
    for i, r in enumerate(rows):
        vis = "visible" if i == 0 else "collapsed"
        c0, c1, c2, c3 = st.columns([.45, 1.5, 1.4, 1.3],vertical_alignment="bottom")
        r["enabled"] = c0.checkbox("​", value=r["enabled"], key=f"seq_on{i}", label_visibility=vis)
        r["depth_m"] = c1.number_input("Depth [m]", value=float(r["depth_m"]), key=f"seq_d{i}", step=10.0, label_visibility=vis)
        r["stroke_m"] = c2.number_input("Stroke [m]", value=float(r["stroke_m"]), key=f"seq_s{i}", step=.05, label_visibility=vis)
        r["mode"] = c3.selectbox("Mode", ["SZ", "SS"], index=0 if r["mode"] == "SZ" else 1, key=f"seq_m{i}", label_visibility=vis)
    return rows


def _unit_panel() -> str:
    us = data.units()
    if not us:
        st.error("The registry came back empty.")
        return ""
    name = st.selectbox("Unit fleet", [u["name"] for u in us], key="unit_name")
    u = data.unit_by_name(name) or us[0]
    p, prm = u["parsed"], u["params"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Stroke", f"{prm['l_s']:.2f} m")
    c2.metric("Comp. cap.", f"{p.get('comp_t') or '—'} t")
    c3.metric("SWL", f"{p.get('swl_t') or '—'} t")

    photo = FIG_DIR / "showcase" / "PHC01.jpg"      # production: figures/<unit>.jpg
    if photo.exists():
        st.image(str(photo))

    d1, d2 = st.columns(2)
    if d1.button("View details", width = "stretch",
                 help="Drawing, designation breakdown and every stored "
                      "parameter, in a window over this page."):
        # Flag only - no st.rerun(). The dispatcher at the foot of app.py
        # opens it in THIS run, which is the run the click belongs to.
        st.session_state.dialog, st.session_state.dialog_unit = "unit", u
    if d2.button("Manage units", width = "stretch",
                 help="Add a unit, derive a variant from one, or retire one."):
        st.session_state.dialog = "units"
    return name


def build_request() -> Dict | None:
    """Read the rail into the API's own request model. Returns None when the
    inputs do not validate - the message is the same one the API would give,
    just without the round trip."""
    with st.sidebar:
        chrome.band("Client inputs", "from the job spec")

        with st.expander("Payload info", expanded=False):
            c1, c2 = st.columns(2)
            air = c1.number_input("Air wt [kg]", value=255000.0, step=1000.0, key="air_kg")
            wet = c2.number_input("Wet wt [kg]", value=202800.0, step=1000.0, key="wet_kg")
            ph = c1.number_input("Payload h [m]", value=7.0, step=.5, key="payload_h")
            rh = c2.number_input("Rigging h [m]", value=36.0, step=.5, key="rigging_h")
            d0 = c1.number_input("Start [m]", value=-50.0, step=10.0, key="start_m",
                                 help="Negative is above the waterline.")
            d1 = c2.number_input("Final [m]", value=1380.0, step=10.0, key="final_m")

        with st.expander("Lifting operations", expanded=False):
            seq = _sequence_editor()

        with st.expander("Environment", expanded=False):
            prof = st.selectbox("Sea temperature profile", PROFILES, key="profile")
            c1, c2 = st.columns(2)
            ta = c1.number_input("Air temp [°C]", value=30.0, step=1.0, key="air_c")
            ts = c2.number_input("Surface temp [°C]", value=25.0, step=1.0, key="surface_c")

        st.markdown("---")
        chrome.band("Safelink inputs", "equipment &amp; setup")

        with st.expander("Unit selection", expanded=False):
            unit_name = _unit_panel()
            application = st.selectbox("Application", APPLICATIONS,
                                       key="application")

        with st.expander("Unit configuration", expanded=False):
            st.caption("Initial charge [barg]")
            c1, c2 = st.columns(2)
            sz = c1.number_input("SZ", value=84.2, step=.1, key="p_sz")
            ss = c2.number_input("SS", value=83.1, step=.1, key="p_ss")
            hp = c1.number_input("HP", value=300.0, step=1.0, key="p_hp")
            lp = c2.number_input("LP", value=0.0, step=1.0, key="p_lp")
            st.caption("Adjustment priority — first feasible action wins")
            prio = st.multiselect("Order", PRIORITIES, key="prio",
                                  default=PRIORITIES[:4])
            orient = st.selectbox("Orientation", ["Rod down", "Rod up"], key="orient")
            hyst = st.number_input("Hysteresis [bar]", value=0.0, step=.1, key="hyst")

    try:
        return SimRequest(
            unit_name=unit_name, application=application, depth_steps=241,
            client_inputs=ClientInputs(
                air_weight_kg=air, wet_weight_kg=wet, payload_height_m=ph,
                rigging_height_m=rh, start_depth_m=d0, final_depth_m=d1,
                lifting_sequence=[r for r in seq if r["enabled"]],
                sea_temp_profile=prof, air_temp_c=ta, surface_temp_c=ts),
            safelink_inputs=SafelinkInputs(
                p_sz_barg=sz, p_ss_barg=ss, p_hp_barg=hp, p_lp_barg=lp,
                priorities=prio, orientation=orient, hysteresis_bar=hyst),
        ).model_dump()
    except ValidationError as exc:
        st.sidebar.error("  \n".join(
            f"**{'.'.join(str(x) for x in e['loc'])}** — {e['msg']}"
            for e in exc.errors()))
        return None


# ================================================================ simulator
KPI = [("P_oil", "Final oil pressure", "barg", "{:.1f}"),
       ("P_ss", "Final SS pressure", "barg", "{:.1f}"),
       ("P_hp", "HP remaining", "barg", "{:.0f}"),
       ("stroke", "Final EQ stroke", "m", "{:.2f}"),
       ("n_used", "N2 drawn from HP", "mol", "{:.0f}"),
       ("energy_kwh", "Booster energy", "kWh", "{:.3f}")]


def _snapshot_name(req: Dict) -> str:
    s, c = req["safelink_inputs"], req["client_inputs"]
    return (f"{s['p_sz_barg']}/{s['p_ss_barg']}/{s['p_hp_barg']} barg · "
            f"{s['orientation'].lower()} · {c['surface_temp_c']} °C")


def _run(req: Dict) -> None:
    auth.touch()
    try:
        st.session_state.result = data.simulate(req, st.session_state.user)
        st.session_state.result_req = req      # what the answer belongs to
    except data.ApiError as exc:
        # A refusal is about the inputs and belongs next to them. An outage is
        # not: it is left to bubble up to the one place that renders it, so
        # the page cannot end up with a flag nobody reads.
        st.session_state.run_error = exc.message


def simulator(req: Dict | None) -> None:
    res = st.session_state.get("result")
    # A case is inputs TOGETHER WITH the results they produced. Comparing the
    # request that produced the result against the one on screen is the whole
    # staleness rule - no bookkeeping, and a reload cannot lose it.
    fresh = bool(res) and req is not None and st.session_state.get("result_req") == req

    with st.sidebar:
        st.markdown("---")
        if st.button("▶  Run simulation", type="primary",
                     width = "stretch", disabled=req is None):
            _run(req)
            st.rerun()
        full = len(st.session_state.compare) >= T.MAX_CASES
        if st.button("Add to compare", width = "stretch",
                     disabled=not fresh or full,
                     help="Comparison is full." if full else
                          "Run the simulation first — a case is a set of inputs "
                          "together with the results they produced."):
            _add_to_compare(req)
            st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("Save case", width = "stretch", disabled=req is None):
            st.session_state.dialog, st.session_state.dialog_req = "save", req
        if c2.button("Load case", width = "stretch"):
            st.session_state.dialog = "load"
        if st.button(f"Compare  ({len(st.session_state.compare)}/{T.MAX_CASES} in new page)", width = "stretch"):
            st.session_state.page = "cmp"
            st.rerun()

    err = st.session_state.pop("run_error", None)
    if err:
        st.error(f"The simulation was refused: {err}")

    if not res:
        st.info("Set up the lift on the left, then press **Run simulation**.")
        return
    
    # Overview on the right and results on the left.
    rs,ov = st.columns([9, 1])
    with rs:
        chrome.band("Simulation results")
        col, ev = res["columns"], res["events"]
        d = col["depth_m"]
        r1 = st.columns([2, 1])
        charts.show(charts.series("Working pressures", "barg", d, [
            {"name": "Main oil / SZ", "y": col["P_sz_barg"], "color": T.SZ},
            {"name": "SS", "y": col["P_ss_barg"], "color": T.SS},
            {"name": "Ambient", "y": col["P_env_bar"], "color": T.INK3, "dash": "dot"},
        ], events=ev), "c_press", r1[0])
        charts.show(charts.series("Equilibrium stroke", "m", d, [
            {"name": "Stroke", "y": col["stroke_m"], "color": T.ACCENT_FG}],
            y0=True, events=ev), "c_stroke", r1[1])

        r2 = st.columns(3)
        charts.show(charts.series("HP reservoir", "barg", d, [
            {"name": "HP", "y": col["P_hp_barg"], "color": T.HP}], y0=True,
            events=ev), "c_hp", r2[0])
        charts.show(charts.series("Gas inventory", "mol", d, [
            {"name": "SZ", "y": col["n_sz"], "color": T.SZ},
            {"name": "SS", "y": col["n_ss"], "color": T.SS},
            {"name": "HP", "y": col["n_hp"], "color": T.HP}], events=ev),
            "c_moles", r2[1])
        charts.show(charts.series("Sea temperature", "°C", d, [
            {"name": "T at depth", "y": col["T_c"], "color": T.TEMP}], y0=True),
            "c_temp", r2[2])
    
    with ov:
        chrome.band("Overview")
        if not fresh:
            st.warning("NB: Rerun", icon="⚠️")

        # Inline styles, not classes: a KPI column that silently loses its stylesheet
        # is still the most-read part of the page.
        lbl = (f"font-size:10.5px;font-weight:600;letter-spacing:.09em;"
            f"text-transform:uppercase;color:{T.INK3};line-height:1.5")
        for k, label, unit, fmt in KPI:
            v = res["kpi"].get(k, float("nan"))
            edge = T.ACCENT if k == "stroke" else T.LINE
            st.html(f'<div style="border-left:2px solid {edge};padding:2px 0 2px 10px">'
                f'<div style="{lbl}">{label}</div>'
                f'<div style="font-family:ui-monospace,monospace;font-size:21px;'
                f'font-weight:500;line-height:1.35">{fmt.format(v)}</div>'
                f'<div style="{lbl}">[{unit}]</div></div>')

        v = res["verdict"]
        ok = bool(v.get("suitable"))
        edge, bg = ((T.OK, "rgba(15,118,110,.07)") if ok
                    else (T.BAD, "rgba(185,28,28,.06)"))
        st.html(f'<div style="border:1px solid {edge};border-left-width:3px;'
            f'padding:8px 12px;background:{bg};font-size:13.5px;line-height:1.6;'
            f'margin:.3rem 0 .7rem">'
            f'<b>{"Unit suitable" if ok else "Not suitable"}</b> &nbsp;·&nbsp; '
            + " &nbsp;·&nbsp; ".join(v.get("lines", [])) + "</div>")

    _status_bar(res)


def _add_to_compare(req: Dict) -> None:
    used = {c["slot"] for c in st.session_state.compare}
    slot = next(i for i in range(T.MAX_CASES) if i not in used)
    st.session_state.compare.append({
        "id": f"r{int(time.time()*1000)}", "slot": slot, "on": True,
        "unit": req["unit_name"], "sub": _snapshot_name(req),
        "req": req, "res": st.session_state.result,
    })


def apply_case(req: Dict) -> None:
    """Put a stored case's inputs back on the rail. The result is dropped on
    purpose: inputs are back, the curves are not, and Add to compare stays off
    until Run. Anything else would file a case whose numbers never belonged."""
    c, s = req["client_inputs"], req["safelink_inputs"]
    st.session_state.update(
        unit_name=req["unit_name"], air_kg=c["air_weight_kg"],
        wet_kg=c["wet_weight_kg"], payload_h=c["payload_height_m"],
        rigging_h=c["rigging_height_m"], start_m=c["start_depth_m"],
        final_m=c["final_depth_m"], profile=c["sea_temp_profile"],
        air_c=c["air_temp_c"], surface_c=c["surface_temp_c"],
        seq=list(c["lifting_sequence"]),
        p_sz=s["p_sz_barg"], p_ss=s["p_ss_barg"], p_hp=s["p_hp_barg"],
        p_lp=s["p_lp_barg"], prio=s["priorities"], orient=s["orientation"],
        hyst=s["hysteresis_bar"], result=None, result_req=None)
    for i, r in enumerate(c["lifting_sequence"]):
        st.session_state[f"seq_on{i}"] = r["enabled"]
        st.session_state[f"seq_d{i}"] = float(r["depth_m"])
        st.session_state[f"seq_s{i}"] = float(r["stroke_m"])
        st.session_state[f"seq_m{i}"] = r["mode"]


def _status_bar(res: Dict) -> None:
    st.html(f'<div style="border-top:1px solid {T.LINE};margin-top:1.2rem;'
        f'padding-top:8px;font-size:11.5px;line-height:1.7;color:{T.INK2};'
        f'display:flex;gap:10px;flex-wrap:wrap">'
        f'<span>Set up the lift on the left, then press Run simulation.</span>'
        f'<span style="margin-left:auto;font-family:ui-monospace,monospace;'
        f'font-size:10.5px;color:{T.INK3};white-space:nowrap">'
        f'{len(st.session_state.compare)}/{T.MAX_CASES} in comparison &nbsp;·&nbsp; '
        f'{res["n_steps"]} depth steps &nbsp;·&nbsp; last run {res["runtime_s"]:.1f} s'
        f' &nbsp;·&nbsp; {res["engine_version"]} &nbsp;·&nbsp; '
        f'{res["input_hash"]} &nbsp;·&nbsp; streamlit {st.__version__}'
        f'</span></div>')


# ================================================================== compare
QUANTITIES = [("P_sz_barg", "Oil / SZ pressure", "barg", True),
              ("P_ss_barg", "SS pressure", "barg", False),
              ("stroke_m", "Equilibrium stroke", "m", True),
              ("P_hp_barg", "HP reservoir", "barg", True),
              ("n_sz", "Gas in SZ chamber", "mol", False),
              ("n_hp", "Gas in HP reservoir", "mol", False),
              ("T_c", "Sea temperature", "°C", False)]


def compare() -> None:
    cases = st.session_state.compare
    with st.sidebar:
        chrome.band("Cases to compare")
        if not cases:
            st.caption("Nothing added yet. Run a simulation, then **Add to compare**.")
        for c in list(cases):
            tag, colour, _ = T.CASE_STYLE[c["slot"]]
            c1, c2, c3 = st.columns([.5, 4, .7])
            c["on"] = c1.checkbox("​", value=c["on"], key=f"on{c['id']}", label_visibility="collapsed")
            c2.html(f"<div style='line-height:1.45'>"
                    f"<span style='color:{colour};font-weight:700'>{tag}</span> "
                    f"<span style='font-size:13px'>{c['unit']}</span><br>"
                    f"<span style='font-size:11px;color:{T.INK3}'>{c['sub']}</span>"
                    f"</div>")
            if c3.button("✕", key=f"del{c['id']}", help="Remove this case"):
                cases.remove(c)
                st.rerun()
        st.caption(f"Up to {T.MAX_CASES} cases. Remove one to add another.")
        st.markdown("---")
        chrome.band("Data to plot")
        picked = [k for k, label, unit, on in QUANTITIES
                  if st.checkbox(f"{label}  [{unit}]", value=on, key=f"q{k}")]

        st.markdown("---")
        if st.button("←  Simulator", width = "stretch"):
            st.session_state.page = "sim"
            st.rerun()

    # chrome.band("Plots")
    shown = [c for c in cases if c["on"]]
    if not shown or not picked:
        st.info("Tick a case and a quantity on the left.")
        return

    grid = st.columns(2)
    for i, key in enumerate(picked):
        label, unit = next((l, u) for k, l, u, _ in QUANTITIES if k == key)
        lines = []
        for c in shown:
            tag, colour, dash = T.CASE_STYLE[c["slot"]]
            lines.append({"name": f"{tag} — {c['unit']}",
                          "y": c["res"]["columns"][key],
                          "color": colour, "dash": dash})
        fig = charts.series(label, unit, shown[0]["res"]["columns"]["depth_m"],
                            lines, y0=key in ("stroke_m", "P_hp_barg"),
                            height=T.CHART_H_CMP)
        charts.show(fig, f"cmp_{key}", grid[i % 2])
