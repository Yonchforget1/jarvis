"""Tests for game engine tools."""

from __future__ import annotations

import pytest
from pathlib import Path

from jarvis.tools.gamedev import (
    SceneBuilder,
    GDScriptBuilder,
    generate_godot_project,
    create_gdscript,
    create_scene,
)


def test_scene_builder():
    scene = SceneBuilder()
    mesh_id = scene.add_sub_resource("BoxMesh", {"size": "Vector3(1, 1, 1)"})
    scene.add_node("Root", "Node3D")
    scene.add_node("Box", "MeshInstance3D", parent=".", properties={
        "mesh": f'SubResource("{mesh_id}")',
    })
    result = scene.build()
    assert "gd_scene" in result
    assert "BoxMesh" in result
    assert 'name="Root"' in result
    assert 'name="Box"' in result
    assert "SubResource" in result


def test_scene_builder_ext_resource():
    scene = SceneBuilder()
    rid = scene.add_ext_resource("res://script.gd", "Script")
    assert rid == 1
    result = scene.build()
    assert 'ext_resource type="Script"' in result
    assert 'path="res://script.gd"' in result


def test_gdscript_builder():
    builder = GDScriptBuilder("CharacterBody3D")
    builder.add_export("speed", "float", "5.0")
    builder.add_var("gravity", "9.8")
    builder.add_ready("print('ready')")
    builder.add_process("position.y -= gravity * delta")
    builder.add_function("jump", "", "velocity.y = 10")
    result = builder.build()
    assert "extends CharacterBody3D" in result
    assert "@export var speed: float = 5.0" in result
    assert "var gravity = 9.8" in result
    assert "func _ready():" in result
    assert "func _process(delta):" in result
    assert "func jump():" in result


def test_gdscript_builder_signals():
    builder = GDScriptBuilder("Node")
    builder.add_signal("health_changed")
    result = builder.build()
    assert "signal health_changed" in result


def test_generate_godot_project(tmp_path):
    project_dir = tmp_path / "test_game"
    result = generate_godot_project(str(project_dir), "TestGame", "A test game")
    assert "Created Godot 4 project" in result
    assert (project_dir / "project.godot").exists()
    assert (project_dir / "main.tscn").exists()
    assert (project_dir / "player.gd").exists()

    # Check project.godot contents
    project_cfg = (project_dir / "project.godot").read_text()
    assert 'config/name="TestGame"' in project_cfg
    assert "main.tscn" in project_cfg

    # Check scene contents
    scene = (project_dir / "main.tscn").read_text()
    assert "Camera3D" in scene
    assert "DirectionalLight3D" in scene
    assert "Player" in scene

    # Check script contents
    script = (project_dir / "player.gd").read_text()
    assert "extends CharacterBody3D" in script
    assert "move_and_slide" in script
    assert "@export var speed" in script


def test_create_gdscript(tmp_path):
    file_path = tmp_path / "test.gd"
    result = create_gdscript(str(file_path), "Sprite2D", "func _ready():\n\tpass")
    assert "Created GDScript" in result
    assert file_path.exists()
    content = file_path.read_text()
    assert "extends Sprite2D" in content
    assert "_ready" in content


def test_create_scene(tmp_path):
    file_path = tmp_path / "test.tscn"
    scene_def = '[gd_scene format=3]\n[node name="Root" type="Node2D"]\n'
    result = create_scene(str(file_path), scene_def)
    assert "Created scene" in result
    assert file_path.exists()
    assert "Node2D" in file_path.read_text()


def test_gdscript_builder_empty():
    builder = GDScriptBuilder("Node")
    result = builder.build()
    assert "extends Node" in result


def test_scene_node_properties():
    scene = SceneBuilder()
    scene.add_node("Light", "PointLight3D", parent=".", properties={
        "light_energy": 2.0,
        "shadow_enabled": True,
    })
    result = scene.build()
    assert "light_energy = 2.0" in result
    assert "shadow_enabled = true" in result
