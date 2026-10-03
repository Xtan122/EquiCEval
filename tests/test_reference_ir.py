"""The AircraftLanding reference must link the ordering binaries (paper Eq 24).

``z_ij + z_ji = 1`` is present in the original paper and in the generated
benchmark ground truth, but was missing from the canonical reference used for
real-LLM evaluation, which made the reference itself ambiguous.
"""
from src.benchmark.reference_ir import make_aircraft_landing_reference


def _has_order_link(ref, a, b):
    return any(
        c.sense == "==" and set(c.coeffs) == {a, b}
        and all(v == 1.0 for v in c.coeffs.values()) and c.constant == -1.0
        for c in ref.constraints
    )


def test_alp_reference_links_ordering_binaries():
    ref = make_aircraft_landing_reference()
    for a, b in (("z12", "z21"), ("z13", "z31"), ("z23", "z32")):
        assert _has_order_link(ref, a, b), f"missing {a} + {b} = 1"


def test_alp_reference_is_no_longer_flagged_ambiguous():
    ref = make_aircraft_landing_reference()
    assert not ref.metadata.get("audit")
