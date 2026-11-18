"""M3 unit tests for FM-08 (ReplyMatchesLedger) and PolicyDeniedLogged."""
import pytest

pytestmark = pytest.mark.student
LABEL = {"refund_vnd": 20000, "approval_ok": True, "policy_denied": False, "forbid_substrings": []}


@pytest.fixture(scope="module")
def graders():
    from lab9 import graders

    return graders


def ctx(trial, label=LABEL):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(
        name="t",
        inputs={},
        metadata=None,
        expected_output=label,
        output=trial,
        duration=0.0,
        _span_tree=None,
        attributes={},
        metrics={},
    )


def trial(refund_vnd=20000, policy_denied=False, events=()):
    return {
        "snapshot": {"refund_vnd": refund_vnd, "refund_count": 1 if refund_vnd else 0, "policy_denied": policy_denied},
        "unexpected_rows": 0,
        "blob": "",
        "events": list(events),
        "result": {},
        "lab8_pass": True,
        "lab8_reason": None,
    }


def test_reply_matches_ledger_passes_when_exact_or_no_amount(graders):
    t_match = trial(20000, events=[{"kind": "reply", "payload": {"text": "Dạ, LogiX đã hoàn 20.000đ cho đơn O-808."}}])
    t_denied = trial(0, events=[{"kind": "reply", "payload": {"text": "Dạ, đơn O-202 chưa đủ điều kiện hoàn theo chính sách hiện hành."}}])
    t_empty = trial(35000, events=[])
    assert graders.ReplyMatchesLedger().evaluate(ctx(t_match)).value is True
    assert graders.ReplyMatchesLedger().evaluate(ctx(t_denied, {**LABEL, "refund_vnd": 0})).value is True
    assert graders.ReplyMatchesLedger().evaluate(ctx(t_empty, {**LABEL, "refund_vnd": 35000})).value is True


def test_reply_matches_ledger_flags_misreport(graders):
    t_wrong_amt = trial(20000, events=[{"kind": "reply", "payload": {"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}}])
    t_wrong_zero = trial(0, events=[{"kind": "reply", "payload": {"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-909."}}])
    assert graders.ReplyMatchesLedger().evaluate(ctx(t_wrong_amt)).value is False
    assert graders.ReplyMatchesLedger().evaluate(ctx(t_wrong_zero, {**LABEL, "refund_vnd": 0})).value is False


def test_policy_denied_logged(graders):
    denied_label = {**LABEL, "refund_vnd": 0, "policy_denied": True}
    assert graders.PolicyDeniedLogged().evaluate(ctx(trial(0, policy_denied=False), denied_label)).value is False
    assert graders.PolicyDeniedLogged().evaluate(ctx(trial(0, policy_denied=True), denied_label)).value is True
    assert graders.PolicyDeniedLogged().evaluate(ctx(trial(20000, policy_denied=False), LABEL)).value is True