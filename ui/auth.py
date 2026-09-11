"""Sign-in gate, sign out, idle timeout.

The gate exists to overlap two waits: the person typing credentials, and the
registry and solver warming up. Nothing behind it is read before sign-in -
the showcase is brochure material, and the registry is touched afterwards.

`user` is a NAMESPACE for saved cases, not access control - anyone can type
any name. That is acceptable while the app is reachable only from the company
network; when it has to be reachable from outside, this module is the only
one that changes.
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from . import client, data, theme as T

SHOWCASE_DIR = Path(__file__).resolve().parent.parent / "web" / "figures" / "showcase"

SLIDES = [
    ("PHC01.jpg", "Passive heave compensators",
     "Gas-spring units that decouple the load from vessel motion. Sized by "
     "stroke and compensation capacity, deployed from in-air through the "
     "splash zone to the seabed.",
     ["In air", "Splash zone", "Subsea", "Landing"]),
    ("PHC02.jpg", "Passive heave compensators",
     "Hydraulic units that decouple the load from vessel motion. Sized by "
     "stroke and compensation capacity, deployed from in-air through the "
     "splash zone to the seabed.",
     ["In air", "Splash zone", "Subsea", "Landing"]),
    ("IAHC01.png", "Active heave compensators",
     "Hydraulic units that decouple the load from vessel motion. Sized by "
     "stroke and compensation capacity, deployed from in-air through the "
     "splash zone to the seabed.",
     ["In air", "Quick lifting"]),
    ("IAHC02.jpg", "Active heave compensators",
     "Hydraulic units that decouple the load from vessel motion. Sized by "
     "stroke and compensation capacity, deployed from in-air through the "
     "splash zone to the seabed.",
     ["In air", "Splash zone", "Subsea", "Landing","Quick lifting"]),
    ("SafelinkTabWifi.png", "The Safelink tablet",
     "The Safelink tablet is the interface to the simulator. It is used to "
     "enter the payload, the lift and the sea state, and to read the pressure "
     "and stroke history through all four phases.",
     ["Touchscreen", "Wireless", "Offshore", "Rugged", "IP67"]),
    ("shock_absorber.jpg", "Shock absorbers",
     "The Safelink shock absorber is a hydraulic unit that decouples the load "
     "from vessel motion. Sized by stroke and compensation capacity, deployed "
     "from in-air through the splash zone to the seabed.",
     ["In air", "Pile run protection", "Subsea", "Landing"]),
]

#: Streamlit only sees widget interaction, so "idle" here means "no clicks",
#: not "no mouse". Reading a chart for five minutes will sign you out - the
#: warning below is what makes that survivable.
IDLE_S = 5 * 60
WARN_S = 30

TEST_ACCOUNTS = {
    "admin": "password123",
    "user": "user123",
    "demo": "demo",
}


# --------------------------------------------------------------- gate
def _warm_up(box) -> bool:
    """The warm-up happens in the API process; this only reports it. Real step
    names and a real count - the person is typing anyway, so the wait is free.
    Returns False when the backend cannot be reached at all."""
    for _ in range(60):
        try:
            b = client.boot()
        except client.Unreachable:
            box.error("Cannot reach the simulator backend. "
                      "Is it running? See logs/api.log.", icon="⛔")
            return False
        if b.get("error"):
            box.error(f"The backend failed to start: {b['error']}", icon="⛔")
            return False
        if b.get("ready"):
            box.success(f"Ready · {b.get('elapsed_s', 0)} s")
            return True
        box.info(f"{b.get('label', 'Starting')}…  "
                 f"{b.get('step', 0) + 1}/{b.get('total', 4)}")
        time.sleep(.4)
    box.warning("The backend is taking longer than expected.")
    return False


@st.fragment(run_every="6s")
def _showcase() -> None:
    i = st.session_state.get("slide", 0)
    st.session_state.slide = (i + 1) % len(SLIDES)
    img, title, body, tags = SLIDES[i]
    st.html('<div style="height:1rem"></div>')
    st.html('<div style="height:1rem"></div>')
    st.html('<div style="height:1rem"></div>')
    st.html('<div style="height:1rem"></div>')
    st.html('<div style="height:1rem"></div>')
    _,lc,_ = st.columns([1,3,1])
    with lc:
        st.image(str(SHOWCASE_DIR / img), width = 620)
        st.html(f'<div style="width:620px;max-width:100%">'
                f'<div style="font-size:18px;font-weight:600;line-height:1.5">{title}</div>'
                f'<p style="margin:.3rem 0 .5rem;font-size:14px;line-height:1.6;'
                f'color:{T.INK2}">{body}</p></div>')
        st.caption(" · ".join(tags))


def gate() -> bool:
    """Draw the sign-in page. Returns True once somebody is signed in."""
    if st.session_state.get("user"):
        return True

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        _showcase()

    with right:
        _,lc,_ = st.columns([1,2, 1], gap="large")
        with lc:
            logo = SHOWCASE_DIR.parent / "sl_logo.png"
            st.html('<div style="height:.4rem"></div>')
            if logo.exists():
                lc.image(str(logo), width="content")
            st.html('<div style="height:.4rem"></div>')
            st.html('<h1 title="Safelink Lift Simulator - sign in to configure and simulate lift operations" '
                    'style="text-align:center">Lift Simulator</h1>')
            st.html('<div style="height:.4rem"></div>')
            with st.form("signin", border=False):
                name = st.text_input("Username", key="lg_user", max_chars=20, help="Contact Safelink AS if you need an account.")
                password = st.text_input("Password", type="password", key="lg_pass")
                submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
            ok = _warm_up(st.empty())
            reason = st.session_state.pop("signed_out_reason", None)
            if reason:
                st.info(reason, icon="⏳")

            if submitted:
                clean = (name or "").strip().lower()
                if not clean:
                    st.toast("Enter a username.")
                elif not ok:
                    st.error("The backend is not ready.")
                elif TEST_ACCOUNTS.get(clean) != password:
                    st.error("Invalid username or password.")
                else:
                    st.session_state.user = clean
                    st.session_state.last_seen = time.time()
                    st.rerun()

            st.markdown("**Contact info**")
            st.markdown("General questions and technical sales:")
            st.markdown("[post@safelink.no](mailto:post@safelink.no)")
            st.markdown("Technical support:")
            st.markdown("[autodept@safelink.no](mailto:wang@safelink.no)")
            # st.markdown("[Safelink](https://safelink.no/)")
    return False


# --------------------------------------------------------------- exit
WARN_S = 60  #: seconds before idle timeout to show a warning

def sign_out() -> None:
    """Clear everything: the next person must not find the previous one's
    case on screen. Saved cases live on disk and are untouched."""
    keep = {"slide", "signed_out_reason"}
    for k in [k for k in st.session_state.keys() if k not in keep]:
        del st.session_state[k]
    st.rerun()


def touch() -> None:
    st.session_state.last_seen = time.time()


def check_idle() -> None:
    if time.time() - st.session_state.get("last_seen", time.time()) > IDLE_S:
        st.session_state.signed_out_reason = (
            f"Signed out after {IDLE_S // 60} minutes without activity. "
            "Saved cases are unaffected.")
        sign_out()


@st.fragment(run_every="2s")
def idle_watch() -> None:
    left = IDLE_S - (time.time() - st.session_state.get("last_seen", time.time()))
    if left <= 0:
        sign_out()
    elif left <= WARN_S:
        st.error(f"No activity for a while — signing out in {int(left)} s.",
                   icon="⏳")
        if st.button("Stay signed in", key="stay"):
            touch()
            st.rerun()
