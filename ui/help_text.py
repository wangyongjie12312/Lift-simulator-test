"""The Help document. Lifted from the reference UI, unchanged in substance.

Sections 3 and 7 are marked as placeholders on purpose: the terminology and
the calculation basis have to come from Safelink so the wording matches
internal usage. A plausible-sounding guess in a reference document is worse
than an admitted gap.
"""

INTRO = """**Reference for all users.** Sections 1 to 6 describe what the
simulator does and how to operate it, and assume no prior familiarity with
heave compensation. Section 7 covers the calculation basis and is intended for
engineering staff."""

SECTIONS = [
    ("1 · Purpose", """
The Lift Simulator determines whether a given Safelink passive heave
compensator (PHC) is suitable for a specified subsea lift.

Vessel motion in a seaway is transmitted through the lifting wire to the
suspended load. A PHC installed in the lifting line acts as a gas spring: it
extends and retracts so that vessel motion is absorbed by the unit rather than
by the wire and the load.

The simulator takes a description of the lift together with a candidate unit,
and reports the behaviour of that unit over the full operation, from lift-off
to seabed landing.
"""),
    ("2 · Selection criterion", """
The compensator consists of a piston in a cylinder. The distance available to
the piston is the unit's **stroke**.

A compensator functions only while the piston remains within that travel. If
the piston reaches either end of the stroke, the unit becomes a rigid link and
no longer compensates; vessel motion is then transmitted directly to the load.

Unit selection therefore reduces to a single condition: **the equilibrium
stroke must remain within the unit's travel over the entire depth range, at the
gas pressures the unit can maintain.** This is the primary acceptance
criterion, and it is shown in the Equilibrium stroke chart.
"""),
    ("3 · Terminology", None),        # placeholder, rendered separately
    ("4 · Operation", """
1. Select the candidate unit under **Safelink inputs → Unit selection**. The
   unit figure and the principal specifications update with the selection.
2. Enter the lift under **Client inputs**: payload weights and geometry, the
   lifting sequence, and the environmental conditions. These values are taken
   from the client's lift specification.
3. Select **Run simulation**.
4. Review the verdict in the Overview band, then the Equilibrium stroke chart.
5. To evaluate an alternative, select **Add to compare**, modify the inputs,
   run again, and add the second result. **Compare** then displays both cases
   on common axes.
"""),
    ("5 · Interpreting the results", """
- **Overview** — Key results at landing depth and the overall verdict. The
  verdict line states the outcome together with the conditions it rests on;
  each condition can be traced to the corresponding chart.
- **Equilibrium stroke** — Piston position against depth. Accepted when the
  curve remains clear of both stroke limits throughout the operation.
- **Working pressures** — Oil, SZ and SS pressures against depth. Expected to
  develop continuously, without abrupt transitions.
- **HP reservoir** — Pressure remaining in high-pressure storage at each
  depth. The acceptance threshold for the reserve at landing depth is to be
  defined.
- **Gas inventory** — Nitrogen quantity in each chamber. Each step corresponds
  to one gas adjustment.
- **Sea temperature** — Temperature profile applied over the depth range.
  Reference information; it accounts for the pressure development with depth.

Each chart can be saved as an image from the toolbar in its corner.
"""),
    ("6 · Cases and comparison", """
A case consists of the **input set**, not the computed results. **Save case**
stores the current inputs; **Load case** restores them. Reopening a stored case
re-runs the solver, so a case always reflects the current calculation method
rather than reproducing an earlier result.

Loading a case restores the inputs but leaves the displayed results unchanged
until **Run simulation** is selected. Results shown are therefore always
attributable to the inputs that produced them.

**Add to compare** records the result currently displayed. It is unavailable
until a simulation has been run, and again after any input is modified.

**Compare** opens the comparison view. The comparison holds up to five cases.
Each case is identified by colour, line style and letter, so that cases remain
distinguishable in print, in monochrome, and under colour-vision deficiency.
"""),
    ("7 · Technical basis", None),    # placeholder
    ("8 · Scope and limitations", """
The simulator is a **screening tool**. It identifies which units merit further
evaluation. It does not replace a full dynamic analysis of the lift: vessel
response amplitude operators, wire dynamics, splash-zone slamming loads and
landing impact are not modelled.
"""),
    ("9 · Sessions", """
Saved cases are stored under your user name. The session signs out after five
minutes without interaction; a warning appears thirty seconds beforehand.
Anything not saved as a case is lost at sign-out.
"""),
]

PLACEHOLDERS = {
    "3 · Terminology": """**Placeholder — to be completed.**

Definitions of the terms used on screen, written for readers without a
heave-compensation background: stroke, equilibrium stroke, SZ and SS chamber,
HP reservoir, initial charge, gauge pressure, gas adjustment, compensation
capacity, SWL, hysteresis, rod orientation, and the unit designation format.

To be supplied by Safelink so that the wording matches internal usage.""",
    "7 · Technical basis": """**Placeholder — to be completed.**

Intended content: equation of state and gas property model, sea-temperature
profile, gas-adjustment arbitration logic, booster energy definition, the
persisted unit parameter set, and the correspondence to the legacy LabVIEW
implementation.""",
}

CURRENT_BUILD = """**Current build.** The lift solver is a placeholder. Only
the sea-temperature profile and the ambient pressure are computed. All other
curves and reported values are representative in shape and magnitude only and
have no physical meaning. **They must not be used for unit selection.**"""
