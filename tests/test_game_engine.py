"""Tests for the Godot 4 game engine pipeline."""

import pytest

from jarvis.tools.game_engine import (
    _IDGen, SceneBuilder, GDScriptBuilder,
)


class TestIDGen:
    def test_ext_increments(self):
        gen = _IDGen()
        assert gen.ext() == 1
        assert gen.ext() == 2
        assert gen.ext() == 3

    def test_sub_increments(self):
        gen = _IDGen()
        assert gen.sub() == 1
        assert gen.sub() == 2

    def test_ext_and_sub_independent(self):
        gen = _IDGen()
        assert gen.ext() == 1
        assert gen.sub() == 1
        assert gen.ext() == 2
        assert gen.sub() == 2


class TestSceneBuilder:
    def test_empty_scene(self):
        builder = SceneBuilder()
        result = builder.build()
        assert "[gd_scene" in result
        assert "format=3" in result

    def test_add_ext_resource(self):
        builder = SceneBuilder()
        rid = builder.add_ext_resource("res://player.gd", "Script")
        assert rid == 1
        result = builder.build()
        assert 'ext_resource type="Script"' in result
        assert 'path="res://player.gd"' in result

    def test_add_sub_resource(self):
        builder = SceneBuilder()
        rid = builder.add_sub_resource("BoxMesh", {"size": "Vector3(1, 1, 1)"})
        assert rid == 1
        result = builder.build()
        assert 'sub_resource type="BoxMesh"' in result
        assert "Vector3(1, 1, 1)" in result

    def test_add_root_node(self):
        builder = SceneBuilder()
        builder.add_node("Root", "Node3D")
        result = builder.build()
        assert '[node name="Root" type="Node3D"]' in result
        # Root node should not have parent
        assert 'parent="."' not in result.split("\n")[
            next(i for i, line in enumerate(result.split("\n")) if "Root" in line)
        ]

    def test_add_child_node(self):
        builder = SceneBuilder()
        builder.add_node("Root", "Node3D")
        builder.add_node("Child", "MeshInstance3D", parent=".")
        result = builder.build()
        assert '[node name="Child" type="MeshInstance3D" parent="."]' in result

    def test_node_with_properties(self):
        builder = SceneBuilder()
        builder.add_node("Root", "Node3D", properties={"visible": True})
        result = builder.build()
        assert "visible = true" in result

    def test_node_with_script(self):
        builder = SceneBuilder()
        rid = builder.add_ext_resource("res://main.gd", "Script")
        builder.add_node("Root", "Node3D", script_id=rid)
        result = builder.build()
        assert f'script = ExtResource("{rid}")' in result

    def test_node_with_groups(self):
        builder = SceneBuilder()
        builder.add_node("Enemy", "CharacterBody3D", groups=["enemies", "targets"])
        result = builder.build()
        assert 'groups=["enemies", "targets"]' in result

    def test_format_value_bool(self):
        builder = SceneBuilder()
        assert builder._format_value(True) == "true"
        assert builder._format_value(False) == "false"

    def test_format_value_number(self):
        builder = SceneBuilder()
        assert builder._format_value(42) == "42"
        assert builder._format_value(3.14) == "3.14"

    def test_format_value_string(self):
        builder = SceneBuilder()
        assert builder._format_value("hello") == '"hello"'

    def test_format_value_godot_types_unquoted(self):
        builder = SceneBuilder()
        assert builder._format_value("Vector3(1, 2, 3)") == "Vector3(1, 2, 3)"
        assert builder._format_value("Color(1, 0, 0, 1)") == "Color(1, 0, 0, 1)"
        assert builder._format_value("SubResource(1)") == "SubResource(1)"
        assert builder._format_value("ExtResource(1)") == "ExtResource(1)"
        assert builder._format_value("Transform3D()") == "Transform3D()"

    def test_format_value_list(self):
        builder = SceneBuilder()
        assert builder._format_value([1, 2, 3]) == "[1, 2, 3]"

    def test_format_value_dict(self):
        builder = SceneBuilder()
        result = builder._format_value({"key": 42})
        assert '"key": 42' in result

    def test_load_steps_auto_calculated(self):
        builder = SceneBuilder()
        builder.add_ext_resource("res://a.gd", "Script")
        builder.add_sub_resource("BoxMesh")
        result = builder.build()
        # 1 ext + 1 sub + 1 = 3
        assert "load_steps=3" in result

    def test_load_steps_manual(self):
        builder = SceneBuilder()
        result = builder.build(load_steps=10)
        assert "load_steps=10" in result

    def test_nested_parent_path(self):
        builder = SceneBuilder()
        builder.add_node("Root", "Node3D")
        builder.add_node("Body", "Node3D", parent=".")
        builder.add_node("Arm", "Node3D", parent="Body")
        result = builder.build()
        assert 'parent="Body"' in result


class TestGDScriptBuilder:
    def test_minimal_script(self):
        builder = GDScriptBuilder("Node3D")
        result = builder.build()
        assert result.startswith("extends Node3D")

    def test_class_name(self):
        builder = GDScriptBuilder("Node")
        builder.set_class_name("MyClass")
        result = builder.build()
        assert "class_name MyClass" in result

    def test_signals(self):
        builder = GDScriptBuilder("Node")
        builder.add_signal("health_changed(new_hp: int)")
        result = builder.build()
        assert "signal health_changed(new_hp: int)" in result

    def test_exports(self):
        builder = GDScriptBuilder("Node")
        builder.add_export("@export var speed: float = 5.0")
        result = builder.build()
        assert "@export var speed: float = 5.0" in result

    def test_variables(self):
        builder = GDScriptBuilder("Node")
        builder.add_var("var health: int = 100")
        result = builder.build()
        assert "var health: int = 100" in result

    def test_onready(self):
        builder = GDScriptBuilder("Node")
        builder.add_onready('@onready var sprite = $Sprite2D')
        result = builder.build()
        assert '@onready var sprite = $Sprite2D' in result

    def test_functions(self):
        builder = GDScriptBuilder("Node")
        builder.add_func("_ready()", "print('hello')\npass")
        result = builder.build()
        assert "func _ready():" in result
        assert "\tprint('hello')" in result

    def test_raw_blocks(self):
        builder = GDScriptBuilder("Node")
        builder.add_raw("enum State { IDLE, RUNNING }")
        result = builder.build()
        assert "enum State { IDLE, RUNNING }" in result

    def test_fluent_api(self):
        """Builder methods should return self for chaining."""
        builder = GDScriptBuilder("Node")
        result = builder.set_class_name("Test").add_signal("s").add_var("var x = 1")
        assert result is builder

    def test_full_script_structure(self):
        builder = GDScriptBuilder("CharacterBody3D")
        builder.set_class_name("Player")
        builder.add_signal("died")
        builder.add_export("@export var speed: float = 5.0")
        builder.add_var("var hp: int = 100")
        builder.add_onready("@onready var anim = $AnimationPlayer")
        builder.add_func("_ready()", "hp = 100")
        builder.add_func("_physics_process(delta)", "velocity = Vector3.ZERO\nmove_and_slide()")
        result = builder.build()

        lines = result.split("\n")
        # Verify ordering: extends, class_name, signal, export, var, onready, funcs
        extends_idx = next(i for i, l in enumerate(lines) if "extends" in l)
        class_idx = next(i for i, l in enumerate(lines) if "class_name" in l)
        signal_idx = next(i for i, l in enumerate(lines) if "signal" in l)
        export_idx = next(i for i, l in enumerate(lines) if "@export" in l)
        var_idx = next(i for i, l in enumerate(lines) if "var hp" in l)
        onready_idx = next(i for i, l in enumerate(lines) if "@onready" in l)
        func_idx = next(i for i, l in enumerate(lines) if "func _ready" in l)

        assert extends_idx < class_idx < signal_idx < export_idx < var_idx < onready_idx < func_idx

    def test_empty_function_body_lines(self):
        builder = GDScriptBuilder("Node")
        builder.add_func("_ready()", "pass\n\nprint('done')")
        result = builder.build()
        assert "\tpass" in result
        assert "\tprint('done')" in result
