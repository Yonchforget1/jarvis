"""Tests for the task planner and planner tools."""

import json
import pytest

from jarvis.planner import TaskPlanner, Plan, SubTask, TaskStatus


class TestSubTask:
    def test_default_status_is_pending(self):
        t = SubTask(id=1, description="Do something")
        assert t.status == TaskStatus.PENDING

    def test_duration_none_when_not_started(self):
        t = SubTask(id=1, description="Do something")
        assert t.duration_ms is None

    def test_duration_calculated(self):
        t = SubTask(id=1, description="Do something", started_at=100.0, completed_at=100.5)
        assert t.duration_ms == pytest.approx(500.0)

    def test_to_dict_minimal(self):
        t = SubTask(id=1, description="Step one")
        d = t.to_dict()
        assert d["id"] == 1
        assert d["description"] == "Step one"
        assert d["status"] == "pending"
        assert "result" not in d
        assert "duration_ms" not in d

    def test_to_dict_with_result(self):
        t = SubTask(id=1, description="Step one", result="Done!")
        d = t.to_dict()
        assert d["result"] == "Done!"

    def test_to_dict_truncates_long_result(self):
        t = SubTask(id=1, description="Step one", result="x" * 1000)
        d = t.to_dict()
        assert len(d["result"]) == 500


class TestPlan:
    def test_empty_plan_progress(self):
        p = Plan(goal="Test")
        assert p.progress == "0/0"

    def test_progress_counts_completed_and_skipped(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
            SubTask(id=2, description="B", status=TaskStatus.SKIPPED),
            SubTask(id=3, description="C", status=TaskStatus.PENDING),
        ])
        assert p.progress == "2/3"

    def test_is_complete_true(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
            SubTask(id=2, description="B", status=TaskStatus.FAILED),
        ])
        assert p.is_complete is True

    def test_is_complete_false_with_pending(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
            SubTask(id=2, description="B", status=TaskStatus.PENDING),
        ])
        assert p.is_complete is False

    def test_next_task_returns_first_pending(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
            SubTask(id=2, description="B", status=TaskStatus.PENDING),
            SubTask(id=3, description="C", status=TaskStatus.PENDING),
        ])
        nxt = p.next_task()
        assert nxt is not None
        assert nxt.id == 2

    def test_next_task_respects_dependencies(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.PENDING),
            SubTask(id=2, description="B", status=TaskStatus.PENDING, depends_on=[1]),
        ])
        nxt = p.next_task()
        assert nxt.id == 1  # task 2 blocked by 1

    def test_next_task_unblocks_after_dependency_done(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
            SubTask(id=2, description="B", status=TaskStatus.PENDING, depends_on=[1]),
        ])
        nxt = p.next_task()
        assert nxt.id == 2

    def test_next_task_none_when_all_done(self):
        p = Plan(goal="Test", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
        ])
        assert p.next_task() is None

    def test_to_dict(self):
        p = Plan(goal="Build app", tasks=[
            SubTask(id=1, description="A", status=TaskStatus.COMPLETED),
        ])
        d = p.to_dict()
        assert d["goal"] == "Build app"
        assert d["progress"] == "1/1"
        assert d["is_complete"] is True
        assert len(d["tasks"]) == 1


class TestTaskPlanner:
    def test_no_plan_initially(self):
        planner = TaskPlanner()
        assert planner.current_plan is None

    def test_create_plan(self):
        planner = TaskPlanner()
        plan = planner.create_plan("Build app", [
            {"description": "Design UI"},
            {"description": "Write code", "tools": ["write_file"]},
            {"description": "Test", "depends_on": [2]},
        ])
        assert plan.goal == "Build app"
        assert len(plan.tasks) == 3
        assert plan.tasks[0].id == 1
        assert plan.tasks[1].tools == ["write_file"]
        assert plan.tasks[2].depends_on == [2]

    def test_current_plan_is_latest(self):
        planner = TaskPlanner()
        planner.create_plan("Plan A", [{"description": "Step 1"}])
        planner.create_plan("Plan B", [{"description": "Step 1"}])
        assert planner.current_plan.goal == "Plan B"

    def test_start_task(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [{"description": "Step 1"}])
        result = planner.start_task(1)
        assert "Started task 1" in result
        assert planner.current_plan.tasks[0].status == TaskStatus.IN_PROGRESS
        assert planner.current_plan.tasks[0].started_at is not None

    def test_complete_task(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [{"description": "Step 1"}])
        planner.start_task(1)
        result = planner.complete_task(1, "All good")
        assert "completed" in result.lower()
        assert planner.current_plan.tasks[0].status == TaskStatus.COMPLETED
        assert planner.current_plan.tasks[0].result == "All good"

    def test_complete_shows_next_task(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [
            {"description": "Step 1"},
            {"description": "Step 2"},
        ])
        planner.start_task(1)
        result = planner.complete_task(1)
        assert "Next:" in result or "next" in result.lower()

    def test_complete_shows_plan_done(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [{"description": "Only step"}])
        planner.start_task(1)
        result = planner.complete_task(1)
        assert "complete" in result.lower()

    def test_fail_task(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [{"description": "Step 1"}])
        planner.start_task(1)
        result = planner.fail_task(1, "Something broke")
        assert "failed" in result.lower()
        assert planner.current_plan.tasks[0].status == TaskStatus.FAILED

    def test_start_no_plan(self):
        planner = TaskPlanner()
        assert "No active plan" in planner.start_task(1)

    def test_start_nonexistent_task(self):
        planner = TaskPlanner()
        planner.create_plan("Test", [{"description": "Step 1"}])
        assert "not found" in planner.start_task(99)

    def test_get_status_no_plan(self):
        planner = TaskPlanner()
        assert "No active plan" in planner.get_status()

    def test_get_status_with_plan(self):
        planner = TaskPlanner()
        planner.create_plan("Build app", [
            {"description": "Step 1"},
            {"description": "Step 2"},
        ])
        status = planner.get_status()
        assert "Build app" in status
        assert "0/2" in status

    def test_list_plans(self):
        planner = TaskPlanner()
        planner.create_plan("A", [{"description": "Step"}])
        planner.create_plan("B", [{"description": "Step"}])
        plans = planner.list_plans()
        assert len(plans) == 2
        assert plans[0]["goal"] == "A"
        assert plans[1]["goal"] == "B"

    def test_step_with_missing_description_gets_default(self):
        planner = TaskPlanner()
        plan = planner.create_plan("Test", [{}])
        assert plan.tasks[0].description == "Step 1"


class TestPlannerTools:
    """Test the planner tool functions directly."""

    def test_create_plan_tool(self):
        from jarvis.tools.planner_tools import create_plan
        steps = json.dumps([{"description": "Step 1"}, {"description": "Step 2"}])
        result = create_plan("Build thing", steps)
        assert "Plan created" in result

    def test_create_plan_invalid_json(self):
        from jarvis.tools.planner_tools import create_plan
        result = create_plan("Goal", "not json")
        assert "Error" in result

    def test_create_plan_empty_list(self):
        from jarvis.tools.planner_tools import create_plan
        result = create_plan("Goal", "[]")
        assert "non-empty" in result.lower() or "Steps must" in result

    def test_plan_status_tool(self):
        from jarvis.tools.planner_tools import create_plan, plan_status
        create_plan("Test", json.dumps([{"description": "Step 1"}]))
        result = plan_status()
        assert "Test" in result

    def test_advance_plan_tool(self):
        from jarvis.tools.planner_tools import create_plan, advance_plan
        create_plan("Test", json.dumps([{"description": "Step 1"}]))
        result = advance_plan(1, "start")
        assert "Started" in result
        result = advance_plan(1, "complete", "done")
        assert "completed" in result.lower()

    def test_advance_plan_unknown_action(self):
        from jarvis.tools.planner_tools import create_plan, advance_plan
        create_plan("Test", json.dumps([{"description": "Step 1"}]))
        result = advance_plan(1, "explode")
        assert "Unknown action" in result
