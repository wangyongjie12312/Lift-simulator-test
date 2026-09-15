"""Modal dialogs.

Everything the reference UI opened as a pop-out window lives here. A real
browser tab is not an option: a Streamlit session is per tab, so a new tab
would arrive signed out and knowing nothing about the current selection. A
modal is what the reference UI actually used for these anyway - it covers the
page, keeps its state, and closing it puts you back where you were.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Dict
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree
from ui.schemas import APPLICATIONS, CaseFilePayload, CaseFileRecord, SimRequest
from pydantic import ValidationError

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
            st.info(help_text.PLACEHOLDERS[title], icon=":material/edit_note:")
        else:
            st.markdown(body)
    st.warning(help_text.CURRENT_BUILD, icon=":material/warning:")
    if st.button("Close", use_container_width=True, key="help_close"):
        st.rerun()


# ------------------------------------------------------------------ cases
@st.dialog("Save case")
def save_case() -> None:
    """A case is the input set, not the curves - so this asks for a name and
    nothing else, and it does not care whether a run is on screen."""
    req = st.session_state.dialog_req
    name = st.text_input("Case name", value=f"{req['unit_name']} case")
    destination = st.radio("Save to", ["Web", "Download file"],
                            horizontal=True, key="case_save_destination")
    record = {"name": name.strip() or "Untitled", "inputs": req}
    if destination == "Web":
        st.caption("Saved under your user name. Reopening it re-runs the solver.")
        c1, c2 = st.columns(2)
        save_clicked = c1.button("Save to Web", type="primary",
                                 use_container_width=True)
        close_clicked = c2.button("Close", use_container_width=True)
    else:
        st.caption("Download a file to keep or open in another simulator session.")
        d1, d2, d3 = st.columns(3)
        d1.download_button("Excel", _case_xlsx([record]), "saved-case.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        d2.download_button("TXT", _case_text([record]), "saved-case.txt",
                           "text/plain", use_container_width=True)
        d3.download_button("JSON", _case_json([record]), "saved-case.json",
                           "application/json", use_container_width=True)
        save_clicked = False
        close_clicked = st.button("Close", use_container_width=True)
    if save_clicked:
        if not name.strip():
            st.error("Give the case a name.")
        else:
            try:
                validated = SimRequest.model_validate(req).model_dump(mode="json")
                data.save_case(st.session_state.user, name.strip(), validated)
                st.success(f"Saved “{name.strip()}” — you can close this window.")
                # st.toast(f"Saved “{name.strip()}”", icon="💾")
                # st.rerun()
            except data.ApiError as exc:
                st.error(exc.message)
    if close_clicked:
        st.rerun()


def _case_records(user: str) -> list[Dict]:
    """Return complete case records for export, not just list metadata."""
    records = []
    for row in data.list_cases(user):
        try:
            records.append(data.load_case(user, row["id"]))
        except data.ApiError:
            continue
    return records


def _validated_record(record: Dict) -> Dict:
    try:
        return CaseFileRecord.model_validate(record).model_dump(mode="json")
    except ValidationError as exc:
        raise ValueError("Invalid case structure: " + "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors())) from exc


def _validated_records(records: list[Dict]) -> list[Dict]:
    return [_validated_record(record) for record in records]


def _case_json(records: list[Dict]) -> bytes:
    payload = CaseFilePayload(cases=_validated_records(records))
    return (json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2)
            .encode("utf-8"))


def _case_text(records: list[Dict]) -> bytes:
    records = _validated_records(records)
    lines = ["Lift Simulator saved cases", "=" * 28, ""]
    for record in records:
        lines.append(f"Case: {record.get('name', 'Untitled')}")
        for key, value in _flatten_inputs(record.get("inputs", {})).items():
            lines.append(f"{key}: {_value_text(value)}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def _flatten_inputs(value: Dict, prefix: str = "") -> Dict[str, object]:
    flat = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            flat.update(_flatten_inputs(item, path))
        else:
            flat[path] = item
    return flat


def _value_text(value: object) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _value_from_text(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _unflatten_inputs(values: Dict[str, object]) -> Dict:
    result: Dict = {}
    for path, value in values.items():
        target = result
        parts = path.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return result


def _xlsx_cell(value: str) -> str:
    escaped = (value.replace("&", "&amp;").replace("<", "&lt;")
               .replace(">", "&gt;").replace('"', "&quot;"))
    return f'<c t="inlineStr"><is><t>{escaped}</t></is></c>'


def _case_xlsx(records: list[Dict]) -> bytes:
    records = _validated_records(records)
    fields = sorted({key for record in records
                     for key in _flatten_inputs(record.get("inputs", {}))})
    rows = [["case_name"] + fields]
    rows.extend([[record.get("name", "Untitled")] + [
        _value_text(_flatten_inputs(record.get("inputs", {})).get(field, ""))
        for field in fields] for record in records])
    sheet_rows = "".join(
        f'<row r="{number}">' + "".join(_xlsx_cell(value)
        for value in row) + "</row>"
        for number, row in enumerate(rows, 1)
    )
    sheet = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
             f"<sheetData>{sheet_rows}</sheetData></worksheet>")
    content_types = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                     "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                     "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                     "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                     "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
                     "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
                     "</Types>")
    workbook = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
                "<sheets><sheet name=\"Cases\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>")
    rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>"
            "</Relationships>")
    workbook_rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                     "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                     "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
                     "</Relationships>")
    out = io.BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", workbook_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return out.getvalue()


def _xlsx_rows(raw: bytes) -> list[list[str]]:
    with ZipFile(io.BytesIO(raw)) as archive:
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows = []
    for row in root.findall(".//x:row", ns):
        values = []
        for cell in row.findall("x:c", ns):
            text = cell.find("x:is/x:t", ns)
            values.append(text.text if text is not None and text.text else "")
        rows.append(values)
    return rows


def _uploaded_cases(uploaded) -> list[Dict]:
    raw = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix.lower()
    if suffix == ".json":
        payload = json.loads(raw.decode("utf-8-sig"))
        records = payload.get("cases", []) if isinstance(payload, dict) else payload
    elif suffix in (".xlsx", ".xlsm"):
        rows = _xlsx_rows(raw)
        headers = rows[0] if rows else []
        if headers == ["name", "inputs"]:
            records = [{"name": row[0], "inputs": json.loads(row[1])}
                       for row in rows[1:] if len(row) >= 2 and row[0].strip()]
        else:
            records = [{"name": row[0], "inputs": _unflatten_inputs({
                field: _value_from_text(row[index])
                for index, field in enumerate(headers[1:], 1)
                if index < len(row) and field and row[index] != ""})}
                       for row in rows[1:] if row and row[0].strip()]
    else:
        text = raw.decode("utf-8-sig")
        if text.lstrip().startswith("Lift Simulator saved cases"):
            records, current, values = [], None, {}
            for line in text.splitlines():
                if line.startswith("Case: "):
                    if current is not None:
                        records.append({"name": current,
                                        "inputs": _unflatten_inputs(values)})
                    current, values = line[6:], {}
                elif current is not None and ": " in line:
                    key, value = line.split(": ", 1)
                    values[key] = _value_from_text(value)
            if current is not None:
                records.append({"name": current,
                                "inputs": _unflatten_inputs(values)})
        else:
            rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
            records = [{"name": row.get("name", "Untitled"),
                        "inputs": json.loads(row["inputs"])} for row in rows]
    if not isinstance(records, list):
        raise ValueError("The file must contain a list of cases.")
    try:
        return CaseFilePayload(cases=records).model_dump(mode="json")["cases"]
    except ValidationError as exc:
        raise ValueError("Invalid case file: " + "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors())) from exc


@st.dialog("Load case", width="large")
def load_case() -> None:
    from .views import apply_case          # late: avoids an import cycle
    source = st.radio("Load from", ["Web", "File"], horizontal=True,
                      key="case_load_source")
    if source == "Web":
        rows = data.list_cases(st.session_state.user)
        if not rows:
            st.info("No saved Web cases yet. Use Save case and choose Web.")
        for r in rows:
            c1, c2, c3, c4 = st.columns([5, 2.2, 1.1, .8])
            c1.write(f"**{r['name']}**")
            c2.caption(r["updated_utc"][:16].replace("T", " "))
            if c3.button("Open", key=f"open{r['id']}", use_container_width=True):
                apply_case(data.load_case(st.session_state.user, r["id"])["inputs"])
                st.success(f"Loaded “{r['name']}” — press Run")
            if c4.button("✕", key=f"delc{r['id']}", help="Delete this case"):
                data.delete_case(st.session_state.user, r["id"])
    else:
        uploaded = st.file_uploader("Open saved case file",
                                    type=["xlsx", "xlsm", "txt", "json"],
                                    key="case_file_open")
        if uploaded is not None:
            try:
                records = _uploaded_cases(uploaded)
                choices = [r["name"] for r in records]
                selected = st.selectbox("Case in file", choices,
                                        key="case_file_choice")
                record = records[choices.index(selected)]
                if st.button("Open file case", type="primary",
                             use_container_width=True):
                    apply_case(record["inputs"])
                    st.success(f"Loaded “{record['name']}” — press Run")
            except (ValueError, KeyError, json.JSONDecodeError,
                    ElementTree.ParseError, OSError, BadZipFile) as exc:
                st.error(f"Could not open that case file: {exc}")
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
