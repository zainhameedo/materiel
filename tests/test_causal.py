"""The estimator has to find the effect we planted, and nothing where there is none."""

import numpy as np
import pytest

from materiel.causal import estimate, load_panel
from materiel.generate import TRUE_EFFECT


@pytest.fixture(scope="module")
def results():
    return {e["label"]: e for e in estimate(load_panel())["estimates"]}


def test_did_recovers_planted_effect(results):
    did = results["Difference-in-differences"]
    # The effect phases in over three months, so the post-period average sits a
    # little closer to zero than TRUE_EFFECT; the interval should still cover a
    # value between the two and exclude zero.
    assert did["ci_high"] < 0
    assert did["ci_low"] <= TRUE_EFFECT * 0.85 <= did["ci_high"]


def test_placebo_is_null(results):
    placebo = results["Placebo: fake launch in Jan 2025"]
    assert placebo["ci_low"] < 0 < placebo["ci_high"]


def test_naive_comparison_gets_the_sign_wrong(results):
    # The reason this analysis exists.
    assert results["Enrolled vs. not enrolled, after launch"]["effect"] > 0


def test_event_study_has_no_pretrend():
    es = estimate(load_panel())["event_study"]
    pre = [r for r in es if -12 <= r["k"] <= -2]
    assert np.mean([r["low"] < 0 < r["high"] for r in pre]) >= 0.8
