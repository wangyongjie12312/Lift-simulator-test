"""Modal dialogs.

Everything the reference UI opened as a pop-out window lives here. A real
browser tab is not an option: a Streamlit session is per tab, so a new tab
would arrive signed out and knowing nothing about the current selection. A
modal is what the reference UI actually used for these anyway - it covers the
page, keeps its state, and closing it puts you back where you were.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import streamlit as st

from . import auth, data, help_text, theme as T

FIG_DIR = Path(__file__).resolve().parent.parent / "web" / "figures"


# ------------------------------------------------------------------ unit
# All five take no arguments and read st.session_state, so every one of them
# is opened exactly the way the two that always worked are.
@st.dialog(f"Unit details", width="large")
def unit_details() -> None:
    unit = st.session_state.dialog_unit
    prm, der, p = unit["params"], unit["derived"], unit["parsed"]
    st.divider()
    st.markdown(f"### General Assembly: {unit['name']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Series", p.get("series") or "—")
    c2.metric("Stroke", f"{prm['l_s']:.2f} m")
    c3.metric("Comp. capacity", f"{p.get('comp_t') or '—'} t")
    c4.metric("SWL", f"{p.get('swl_t') or '—'} t")

    ga = FIG_DIR / "showcase" / "ga.png"
    if ga.exists():
        st.image(str(ga), caption="General arrangement — example drawing")

    st.divider()
    st.markdown("### Detailed parameters")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Stored parameters")
        st.caption("The twelve fields the old TDMS persisted.")
        st.dataframe([{"Parameter": k, "Value": v} for k, v in prm.items()],
                     hide_index=True, use_container_width=True, height=430)
    with right:
        st.markdown("#### Derived")
        st.caption("Recomputed from the geometry on every read.")
        st.dataframe([{"Quantity": k, "Value": round(v, 6)}
                      for k, v in der.items()],
                     hide_index=True, use_container_width=True)
        st.markdown("#### Record")
        st.write(f"**Origin** {unit['origin']}  \n"
                 f"**Measured** {'yes' if unit['measured'] else 'no'}  \n"
                 f"**Serial** {p.get('serial') or '—'}")
        if unit.get("note"):
            st.info(unit["note"])
    
    st.divider()
    st.markdown("### Application area")
    st.write(", ".join(unit["applications"]) or "—")
    st.divider()
    
    if st.button("Close", use_container_width=True):
        st.rerun()


@st.dialog("Manage units", width="large")
def manage_units() -> None:
    """New / Edit as variant / Delete.

    Edit never overwrites: a unit is referenced by saved cases, so changing
    one in place would make old results unreproducible. The API enforces
    that; this form only makes the rule visible.
    """
    fields = data.unit_fields()
    us = data.units()
    user = st.session_state.user
    tab_new, tab_edit, tab_del = st.tabs(["New", "Edit as variant", "Delete"])

    # ---------------------------------------------------------------- new
    with tab_new:
        st.caption("Name format: `<series>-<stroke mm> <capacity>/<SWL>-<serial>`, "
                   "e.g. `X-4500 325/400-004`. The parsed figures on screen come "
                   "from the name, so a name off the format shows blanks.")
        name = st.text_input("Unit name", key="nu_name",
                             placeholder="X-4500 325/400-004")
        vals = _param_grid(fields, {f["key"]: 0.0 for f in fields}, "nu")
        apps = st.multiselect("Application area", APPLICATIONS, key="nu_apps")
        note = st.text_area("Note", key="nu_note", height=70)
        if st.button("Create unit", type="primary", use_container_width=True,
                     key="nu_go"):
            if not name.strip():
                st.error("Give the unit a name.")
            else:
                try:
                    out = data.create_unit(user, name.strip(), vals, apps, note)
                    st.success(f"Created “{out['name']}”. Close this window and "
                               "pick it in Unit selection.")
                except data.ApiError as exc:
                    st.error(exc.message)

    # ------------------------------------------------------------- variant
    with tab_edit:
        base = st.selectbox("Base unit", [u["name"] for u in us], key="ev_base")
        b = next(u for u in us if u["name"] == base)
        st.caption(f"`{base}` is a **{b['origin']}** unit. Editing always writes "
                   "a NEW unit — the original is referenced by saved cases and "
                   "is never overwritten.")
        new_name = st.text_input("New unit name", key="ev_name",
                                 placeholder=f"{base} v2  (blank = automatic)")
        vals = _param_grid(fields, b["params"], "ev")
        if st.button("Save as new unit", type="primary",
                     use_container_width=True, key="ev_go"):
            changed = {k: v for k, v in vals.items()
                       if abs(v - float(b["params"][k])) > 1e-12}
            if not changed:
                st.warning("Nothing changed — adjust a parameter first.")
            else:
                try:
                    out = data.create_variant(user, base, changed,
                                              new_name.strip() or None)
                    st.success(f"Created “{out['name']}” with "
                               f"{len(changed)} changed parameter(s).")
                except data.ApiError as exc:
                    st.error(exc.message)

    # -------------------------------------------------------------- delete
    with tab_del:
        victim = st.selectbox("Unit", [u["name"] for u in us], key="du_name")
        st.caption("Soft delete: the record stays in the registry with "
                   "`state = 0`, so a saved case that names this unit still "
                   "resolves it. It just stops appearing in the list.")
        if st.button("Delete unit", use_container_width=True, key="du_go"):
            try:
                data.delete_unit(user, victim)
                # the selectbox on the rail still holds the deleted name; drop
                # it or Streamlit raises on a value that is no longer an option
                if st.session_state.get("unit_name") == victim:
                    st.session_state.pop("unit_name", None)
                st.success(f"Deleted “{victim}”.")
            except data.ApiError as exc:
                st.error(exc.message)

    if st.button("Close", use_container_width=True, key="mu_close"):
        st.rerun()


#: kept in step with core.schema.APPLICATIONS - the API does not serve it yet
APPLICATIONS = ["Splash zone", "Subsea landing", "Resonance", "Salvage"]


def _param_grid(fields, values, prefix: str) -> Dict[str, float]:
    """The twelve persisted fields, three across. Labels and units come from
    the API so there is only one definition of the parameter list."""
    out, cols = {}, st.columns(3)
    for i, f in enumerate(fields):
        label = f"{f['label']}" + (f" [{f['unit']}]" if f["unit"] else "")
        out[f["key"]] = cols[i % 3].number_input(
            label, value=float(values.get(f["key"], 0.0)),
            key=f"{prefix}_{f['key']}", step=.01, format="%.5f")
    return out


# ------------------------------------------------------------------ help
@st.dialog("Using the lift simulator", width="large")
def help_doc() -> None:
    st.markdown(help_text.INTRO)
    for title, body in help_text.SECTIONS:
        st.html(f'<div style="font-size:11.5px;font-weight:700;'
                f'letter-spacing:.1em;text-transform:uppercase;'
                f'color:{T.ACCENT_FG};margin:1.3rem 0 .3rem;line-height:1.8">'
                f'{title}</div>')
        if body is None:
            # Marked, not guessed: a plausible-sounding definition in a
            # reference document is worse than an admitted gap.
            st.info(help_text.PLACEHOLDERS[title], icon="📝")
        else:
            st.markdown(body)
    st.warning(help_text.CURRENT_BUILD, icon="⚠️")
    if st.button("Close", use_container_width=True, key="help_close"):
        st.rerun()


# ------------------------------------------------------------------ cases
@st.dialog("Save case")
def save_case() -> None:
    """A case is the input set, not the curves - so this asks for a name and
    nothing else, and it does not care whether a run is on screen."""
    req = st.session_state.dialog_req
    st.caption("Stored under your user name. Reopening it re-runs the solver, "
               "so a case always reflects the current calculation method.")
    name = st.text_input("Case name", value=f"{req['unit_name']} case")
    c1, c2 = st.columns(2)
    if c1.button("Save", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Give the case a name.")
        else:
            try:
                data.save_case(st.session_state.user, name.strip(), req)
                # st.success(f"Saved “{name.strip()}” — you can close this window.")
                st.toast(f"Saved “{name.strip()}”", icon="💾")
                # st.rerun()
            except data.ApiError as exc:
                st.error(exc.message)
    if c2.button("Close", use_container_width=True):
        st.rerun()


@st.dialog("Load case", width="large")
def load_case() -> None:
    from .views import apply_case          # late: avoids an import cycle
    rows = data.list_cases(st.session_state.user)
    if not rows:
        st.info("No saved cases yet. Set up a lift and use **Save case**.")
    for r in rows:
        c1, c2, c3, c4 = st.columns([5, 2.2, 1.1, .8])
        c1.write(f"**{r['name']}**")
        c2.caption(r["updated_utc"][:16].replace("T", " "))
        if c3.button("Open", key=f"open{r['id']}", use_container_width=True):
            apply_case(data.load_case(st.session_state.user, r["id"])["inputs"])
            # st.success(f"Loaded “{r['name']}” — press Run")
            st.toast(f"Loaded “{r['name']}”", icon="📂")
            # st.session_state.toast_msg = f"Loaded “{r['name']}” — press Run"
            # st.rerun()
        if c4.button("✕", key=f"delc{r['id']}", help="Delete this case"):
            data.delete_case(st.session_state.user, r["id"])
            # st.rerun()
    st.caption("Loading restores the inputs and leaves the results on screen "
               "untouched until you press Run — so what you see always belongs "
               "to the inputs that produced it.")
    if st.button("Close", use_container_width=True, key="load_close"):
        st.rerun()


# ------------------------------------------------------------------ exit
@st.dialog("Sign out")
def sign_out() -> None:
    st.write("You will be returned to the sign-in page.")
    st.caption("Saved cases are kept. Anything on screen that has not been "
               "saved as a case is lost.")
    c1, c2 = st.columns(2)
    if c1.button("Sign out", type="primary", use_container_width=True):
        auth.sign_out()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()
