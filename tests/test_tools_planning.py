"""Tests for planning tools."""

from __future__ import annotations

import pytest

from jarvis.tools.planning import (
    create_plan,
    get_plan,
    update_step,
    list_plans,
    get_next_step,
    _plans,
)


@pytest.fixture(autouse=True)
def clean_plans():
    """Clear plans between tests."""
    _plans.clear()
    yield
    _plans.clear()


def test_create_plan():
    result = create_plan("Build a website", ["Design layout", "Write HTML", "Add CSS", "Deploy"])
    assert "Plan created" in result
    assert "Build a website" in result
    assert "4" in result  # 4 steps


def test_get_plan():
    create_plan("Test goal", ["Step 1", "Step 2"])
    plan_id = list(_plans.keys())[0]
    result = get_plan(plan_id)
    assert "Test goal" in result
    assert "Step 1" in result
    assert "Step 2" in result
    assert "0/2" in result  # no steps completed yet


def test_get_plan_not_found():
    result = get_plan("nonexistent")
    assert "not found" in result


def test_update_step():
    create_plan("Test", ["Step A", "Step B"])
    plan_id = list(_plans.keys())[0]

    result = update_step(plan_id, "step_1", "in_progress")
    assert "in_progress" in result

    result = update_step(plan_id, "step_1", "completed", "Done!")
    assert "completed" in result

    # Check plan status
    plan_status = get_plan(plan_id)
    assert "[x]" in plan_status  # step 1 completed
    assert "1/2" in plan_status


def test_plan_completes():
    create_plan("Test", ["A", "B"])
    plan_id = list(_plans.keys())[0]

    update_step(plan_id, "step_1", "completed", "done")
    update_step(plan_id, "step_2", "completed", "done")

    plan = _plans[plan_id]
    assert plan.status == "completed"


def test_plan_fails():
    create_plan("Test", ["A", "B"])
    plan_id = list(_plans.keys())[0]

    update_step(plan_id, "step_1", "failed", "error occurred")

    plan = _plans[plan_id]
    assert plan.status == "failed"


def test_list_plans():
    create_plan("Plan 1", ["A"])
    create_plan("Plan 2", ["B", "C"])
    result = list_plans()
    assert "Plan 1" in result
    assert "Plan 2" in result


def test_list_plans_empty():
    result = list_plans()
    assert "No plans" in result


def test_get_next_step():
    create_plan("Test", ["Step 1", "Step 2", "Step 3"])
    plan_id = list(_plans.keys())[0]

    result = get_next_step(plan_id)
    assert "step_1" in result

    update_step(plan_id, "step_1", "completed")
    result = get_next_step(plan_id)
    assert "step_2" in result


def test_get_next_step_all_done():
    create_plan("Test", ["A"])
    plan_id = list(_plans.keys())[0]
    update_step(plan_id, "step_1", "completed")
    result = get_next_step(plan_id)
    assert "All steps" in result
