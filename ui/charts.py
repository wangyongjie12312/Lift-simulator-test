"""Plotly figures. One quantity per chart - no dual axes, one scale each.

Every axis carries major ticks with a light grid and minor ticks in between:
these are read to take a value off the curve at a given depth, so an axis with
no reference lines makes the chart decorative rather than useful.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import plotly.graph_objects as go

from . import theme as T

AXIS = dict(
    showline=True, linecolor=T.INK3, linewidth=1, mirror=False,
    showgrid=True, gridcolor=T.GRID, gridwidth=1,
    ticks="outside", ticklen=5, tickwidth=1, tickcolor=T.INK3,
    tickfont=dict(size=10.5, color=T.INK3),
    # minor ticks divide each major interval; the grid line is fainter so it
    # reads as a subdivision rather than as another value
    minor=dict(ticks="outside", ticklen=3, tickcolor=T.LINE,
               showgrid=True, gridcolor=T.GRID_MINOR, gridwidth=.6,
               nticks=5),
    zeroline=False, automargin=True,
)

LAYOUT = dict(
    template="simple_white", height=T.CHART_H,
    margin=dict(l=8, r=14, t=74, b=8),      # keep the title inside the frame
    hovermode="x unified", showlegend=True,
    legend=dict(orientation="h", y=1.02, x=.5, xanchor="center",
                yanchor="bottom", font=dict(size=10.5),
                bgcolor="rgba(0,0,0,0)"),
    font=dict(family="Montserrat, sans-serif", size=11, color=T.INK2),
    title=dict(x=.5, xanchor="center", y=.94, yanchor="top",
               font=dict(size=16, color=T.INK)),
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
)


def series(title: str, unit: str, depth: Sequence[float], lines: List[Dict],
           y0: bool = False, events: Sequence[Dict] = (),
           height: int | None = None) -> go.Figure:
    """lines: [{name, y, color, dash?}]"""
    f = go.Figure()
    f.update_layout(**LAYOUT)
    if height:
        f.update_layout(height=height)
    f.update_layout(title_text=f"{title}  [{unit}]")
    f.update_xaxes(**AXIS, title=dict(text="Depth [m]", font=dict(size=10.5),
                                      standoff=6))
    f.update_yaxes(**AXIS, title=dict(text=unit, font=dict(size=10.5),
                                      standoff=6),
                   rangemode="tozero" if y0 else "normal")
    for ln in lines:
        f.add_trace(go.Scatter(
            x=depth, y=ln["y"], name=ln["name"], mode="lines",
            line=dict(color=ln["color"], width=2, dash=ln.get("dash", "solid")),
            hovertemplate="%{y:.2f} " + unit + "<extra>" + ln["name"] + "</extra>"))
    # Gas adjustments are the moments the controller acted - the reason a curve
    # has a step in it, so they belong on the chart, not in a table.
    for e in events:
        f.add_vline(x=e.get("depth_m", 0), line_width=1, line_dash="dot",
                    line_color=T.ACCENT_FG, opacity=.5)
    return f


def show(fig: go.Figure, key: str, st) -> None:
    st.plotly_chart(fig, width = "stretch", key=key,
                    config={"displaylogo": False,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                            "toImageButtonOptions": {"format": "png", "scale": 2}})
