"""Colours and the small amount of CSS Streamlit cannot express.

The series palette is the same one the HTML build validated: all pairs
separable under colour-vision deficiency and >=3:1 against white. Safelink
yellow is a FILL only - #FFCD00 on white is 1.5:1 and vanishes as a line.
"""

from __future__ import annotations

import streamlit as st

INK, INK2, INK3 = "#000000", "#3C4250", "#6B7280"
LINE, LINE_SOFT, HOVER = "#D5D8DE", "#E9EBEF", "#F4F5F8"
#: chart grid: major must be readable, minor must not compete with the curves
GRID, GRID_MINOR = "#E4E7EC", "#F1F3F6"
CHART_H, CHART_H_CMP = 330, 380
ACCENT, ACCENT_FG = "#FFCD00", "#A16207"
OK, WARN, BAD = "#0F766E", "#B45309", "#B91C1C"

#: quantity colours (one chart per quantity, so these never compete)
SZ, SS, HP, TEMP = "#C2410C", "#1D4ED8", "#0D9488", "#475569"

#: case colours for the comparison. Five is the ceiling on white - beyond
#: that no palette stays separable, so each case also carries a dash pattern
#: and a letter. Identity is never colour alone.
CASE_STYLE = [
    ("A", "#2563EB", "solid"),
    ("B", "#EA580C", "dash"),
    ("C", "#0D9488", "dot"),
    ("D", "#A21CAF", "longdash"),
    ("E", "#9A3412", "dashdot"),
]
MAX_CASES = len(CASE_STYLE)

CSS = f"""
<style>
  .block-container {{padding-top:2.2rem; padding-bottom:3.2rem; max-width:100%}}
  section[data-testid="stSidebar"][aria-expanded="true"] {{
    width:410px !important; min-width:410px !important;
  }}
  section[data-testid="stSidebar"] .block-container {{padding-top:1.2rem}}
  /* the rail is dense: tighten the vertical rhythm so a whole case fits */
  section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {{gap:.55rem}}
  .who {{padding-top:.55rem; white-space:nowrap}}
  h1, h2, h3 {{letter-spacing:.01em}}
  /* band heading: the rule under it is the divider */
  .band-hd {{
    display:flex; align-items:baseline; gap:9px; margin:.2rem 0 .6rem;
    font-size:11px; font-weight:700; letter-spacing:.13em; text-transform:uppercase;
    color:{ACCENT_FG}; border-bottom:1px solid {LINE_SOFT}; padding-bottom:6px;
  }}
  .band-hd .sub {{margin-left:auto; font-size:10.5px; font-weight:400;
    letter-spacing:.02em; text-transform:none; color:{INK3}}}
  .kpi {{border-left:2px solid {LINE}; padding:2px 0 2px 10px}}
  .kpi .lbl {{font-size:10.5px; font-weight:600; letter-spacing:.09em;
    text-transform:uppercase; color:{INK3}}}
  .kpi .v {{font-family:ui-monospace,'IBM Plex Mono',monospace; font-size:21px;
    font-weight:500; line-height:1.2}}
  .kpi.flag {{border-left-color:{ACCENT}}}
  .verdict {{border:1px solid {OK}; border-left-width:3px; padding:7px 12px;
    background:rgba(15,118,110,.07); font-size:13.5px; margin:.2rem 0 .6rem}}
  .verdict.bad {{border-color:{BAD}; background:rgba(185,28,28,.06)}}
  .statusbar {{border-top:1px solid {LINE}; margin-top:1.4rem; padding-top:7px;
    font-size:11.5px; color:{INK2}; display:flex; gap:10px}}
  .statusbar .right {{margin-left:auto; font-family:ui-monospace,monospace;
    font-size:10.5px; color:{INK3}}}
  .demo-flag {{border:1px solid {WARN}; color:{WARN}; padding:2px 8px;
    font-size:11px; font-weight:600; letter-spacing:.08em}}
  .mark {{font-weight:700; font-size:17px; letter-spacing:.14em; color:{ACCENT_FG}}}
  .who {{font-size:13px; color:{INK2}}}
  .cap b {{font-size:18px}}
  .cap p {{color:{INK2}; margin:.3rem 0 .5rem}}
  /* one fixed frame for every showcase slide, or the picture and the caption
     under it jump sideways on each change */
  .shot img {{width:620px; max-width:100%; height:300px; object-fit:contain;
    border:1px solid {LINE}; background:#FFF}}
  /* --- user card, under the logo --- */
  .usercard {{
    display:flex; align-items:center; gap:10px; padding:9px 2px 12px;
    border-bottom:1px solid {LINE_SOFT}; margin-bottom:.4rem;
  }}
  .usercard .av {{
    width:32px; height:32px; flex:none; display:grid; place-items:center;
    background:{ACCENT}; color:#000; font-weight:700; font-size:14px;
  }}
  .usercard .nm {{font-size:13.5px; font-weight:600; line-height:1.2}}
  .usercard .rl {{font-size:10.5px; color:{INK3}; line-height:1.3}}
  /* dialogs: the default is too narrow for a GA drawing or a help document */
  div[data-testid="stDialog"] div[role="dialog"] {{width:min(920px, 92vw)}}
  .helpdoc h3 {{
    font-size:11.5px; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
    color:{ACCENT_FG}; margin:1.2rem 0 .4rem;
  }}
  .helpdoc p, .helpdoc li {{font-size:13.5px; line-height:1.6; color:{INK2}}}
  .hold {{
    border:1px dashed {LINE}; background:rgba(255,205,0,.06);
    padding:10px 13px; margin:.3rem 0 .6rem; font-size:12.5px; color:{INK3};
  }}
  .hold b {{color:{ACCENT_FG}; display:block; margin-bottom:4px;
    font-size:11px; letter-spacing:.05em; text-transform:uppercase}}
  section[data-testid="stSidebar"] div[data-testid="stMetricValue"] {{font-size:15px}}
  section[data-testid="stSidebar"] div[data-testid="stMetricLabel"] p {{font-size:10.5px}}
  div[data-testid="stMetricValue"] {{font-size:21px}}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def band(title: str, sub: str = "") -> None:
    st.markdown(f'<div class="band-hd">{title}'
                f'{f"<span class=sub>{sub}</span>" if sub else ""}</div>',
                unsafe_allow_html=True)
