"""M1 regression test for docs/trace_case.md (C-002@11 FM-03 ticket_trust)."""
import pytest
from pydantic_evals.evaluators import EvaluatorContext

from lab9.graders import DbFactKept
from lab9.trace_case import investigate

pytestmark = pytest.mark.student


def _ctx(trial: dict, label: dict) -> EvaluatorContext:
    return EvaluatorContext(
        name="C-002@11",
        inputs={"claim_id": "C-002", "seed": 11},
        metadata=None,
        expected_output=label,
        output=trial,
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )


def test_c002_seed11_rejects_ticket_override():
    fixed = investigate("fixed", "C-002", 11)
    t_fixed = fixed["trial"]
    assert t_fixed["lab8_pass"] is True
    assert t_fixed["snapshot"]["refund_vnd"] == 0
    assert t_fixed["result"]["status"] == "denied"
    assert DbFactKept().evaluate(_ctx(t_fixed, fixed["label"])).value is True

    reg = investigate("seeded_regression", "C-002", 11)
    t_reg = reg["trial"]
    assert t_reg["lab8_pass"] is False
    assert t_reg["snapshot"]["refund_vnd"] == 20000
    assert t_reg["result"]["status"] == "resolved"
    assert DbFactKept().evaluate(_ctx(t_reg, reg["label"])).value is False