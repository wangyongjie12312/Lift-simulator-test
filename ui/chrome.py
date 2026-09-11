"""Page furniture: the title row and the sidebar head.

Built from Streamlit's own layout primitives with INLINE styles, not from
classes in an injected stylesheet. An injected <style> block is one thing
between the app and the browser that can go missing - and when it does, a
flex row silently becomes three stacked lines. Inline attributes cannot be
dropped without dropping the element itself.
"""

from __future__ import annotations

import streamlit as st

from . import theme as T


def title_row(page: str) -> None:
    """SAFELINK · Lift Simulator, with the demo badge on the right.

    line-height and padding are explicit: the default line box clips the
    descenders of a letter-spaced 17px face on some platforms.
    """
    where = "" if page == "sim" else " &nbsp;·&nbsp; Compare cases"
    left, right = st.columns([5, 1.7], vertical_alignment="center")
    left.html(f'<div style="line-height:1.6;padding:6px 0 10px;white-space:nowrap;'
        f'overflow:visible">'
        f'<span style="font-weight:700;font-size:17px;letter-spacing:.14em;'
        f'color:{T.ACCENT_FG}">SAFELINK</span>'
        f'<span style="font-weight:500;font-size:15px;color:{T.INK2};'
        f'margin-left:14px">Lift Simulator{where}</span></div>')
    # right.html(f'<div style="text-align:right;line-height:1.6;padding:6px 0 10px">'
    #     f'<span style="border:1px solid {T.WARN};color:{T.WARN};padding:3px 9px;'
    #     f'font-size:11px;font-weight:600;letter-spacing:.08em;'
    #     f'white-space:nowrap">DEMO · illustrative data</span></div>')


def sidebar_head(user: str) -> None:
    """Who you are, then the two things that are not part of the lift.

    Columns rather than a flex div: the avatar and the name stay side by side
    whatever happens to the stylesheet.
    """
    av, txt = st.columns([1, 4.2], vertical_alignment="center")
    av.html(f'<div style="width:34px;height:34px;background:{T.ACCENT};color:#000;'
        f'display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;font-size:15px">{user[0].upper()}</div>')
    txt.html(f'<div style="font-size:13.5px;font-weight:600;line-height:1.3">{user}</div>'
        f'<div style="font-size:10.5px;color:{T.INK3};line-height:1.35">')


def band(title: str, sub: str = "") -> None:
    """Section heading with its rule. Inline, for the same reason as above."""
    st.html(f'<div style="display:flex;align-items:baseline;gap:9px;'
        f'margin:.2rem 0 .6rem;font-size:11px;font-weight:700;'
        f'letter-spacing:.13em;text-transform:uppercase;color:{T.ACCENT_FG};'
        f'border-bottom:1px solid {T.LINE_SOFT};padding-bottom:6px;'
        f'line-height:1.7">{title}'
        + (f'<span style="margin-left:auto;font-size:10.5px;font-weight:400;'
           f'letter-spacing:.02em;text-transform:none;color:{T.INK3}">{sub}</span>'
           if sub else "")
        + '</div>')
