"""Godot 4 game engine tools – create complete playable projects."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from textwrap import dedent

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tools.gamedev")

# Godot binary location
_GODOT = os.environ.get("GODOT_PATH", r"C:\Godot\godot.exe")


def _ensure_project_dir(project_path: str) -> Path:
    """Create and return project directory."""
    path = Path(project_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


class SceneBuilder:
    """Builds Godot 4 .tscn scene files."""

    def __init__(self) -> None:
        self._ext_resources: list[str] = []
        self._sub_resources: list[str] = []
        self._nodes: list[str] = []
        self._ext_id = 0
        self._sub_id = 0

    def add_ext_resource(self, path: str, rtype: str) -> int:
        self._ext_id += 1
        self._ext_resources.append(
            f'[ext_resource type="{rtype}" path="{path}" id="ExtResource_{self._ext_id}"]'
        )
        return self._ext_id

    def add_sub_resource(self, rtype: str, properties: dict | None = None) -> int:
        self._sub_id += 1
        lines = [f'[sub_resource type="{rtype}" id="SubResource_{self._sub_id}"]']
        if properties:
            for key, val in properties.items():
                lines.append(f"{key} = {_godot_value(val)}")
        self._sub_resources.append("\n".join(lines))
        return self._sub_id

    def add_node(
        self,
        name: str,
        ntype: str,
        parent: str = "",
        properties: dict | None = None,
    ) -> None:
        parts = [f'[node name="{name}" type="{ntype}"']
        if parent:
            parts[0] += f' parent="{parent}"'
        parts[0] += "]"
        if properties:
            for key, val in properties.items():
                parts.append(f"{key} = {_godot_value(val)}")
        self._nodes.append("\n".join(parts))

    def build(self) -> str:
        sections = ['[gd_scene load_steps=2 format=3]', ""]
        if self._ext_resources:
            sections.extend(self._ext_resources)
            sections.append("")
        if self._sub_resources:
            sections.extend(self._sub_resources)
            sections.append("")
        sections.extend(self._nodes)
        return "\n\n".join(sections) + "\n"


class GDScriptBuilder:
    """Builds Godot 4 GDScript files."""

    def __init__(self, extends: str = "Node") -> None:
        self.extends = extends
        self._signals: list[str] = []
        self._exports: list[str] = []
        self._vars: list[str] = []
        self._ready: list[str] = []
        self._process: list[str] = []
        self._functions: list[str] = []

    def add_signal(self, name: str) -> None:
        self._signals.append(f"signal {name}")

    def add_export(self, name: str, gtype: str, default: str = "") -> None:
        if default:
            self._exports.append(f"@export var {name}: {gtype} = {default}")
        else:
            self._exports.append(f"@export var {name}: {gtype}")

    def add_var(self, name: str, value: str = "") -> None:
        if value:
            self._vars.append(f"var {name} = {value}")
        else:
            self._vars.append(f"var {name}")

    def add_ready(self, code: str) -> None:
        self._ready.append(code)

    def add_process(self, code: str) -> None:
        self._process.append(code)

    def add_function(self, name: str, args: str, body: str) -> None:
        self._functions.append(f"func {name}({args}):\n{_indent(body)}")

    def build(self) -> str:
        lines = [f"extends {self.extends}", ""]
        if self._signals:
            lines.extend(self._signals)
            lines.append("")
        if self._exports:
            lines.extend(self._exports)
            lines.append("")
        if self._vars:
            lines.extend(self._vars)
            lines.append("")
        if self._ready:
            lines.append("func _ready():")
            for code in self._ready:
                lines.append(_indent(code))
            lines.append("")
        if self._process:
            lines.append("func _process(delta):")
            for code in self._process:
                lines.append(_indent(code))
            lines.append("")
        if self._functions:
            lines.extend(self._functions)
        return "\n".join(lines) + "\n"


def _indent(text: str, level: int = 1) -> str:
    prefix = "\t" * level
    return "\n".join(prefix + line if line.strip() else "" for line in text.split("\n"))


def _godot_value(val) -> str:
    """Convert Python value to Godot scene format."""
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        if val.startswith("SubResource(") or val.startswith("ExtResource("):
            return val
        if val.startswith("Vector") or val.startswith("Color"):
            return val
        return f'"{val}"'
    if isinstance(val, (list, tuple)):
        return f"Vector3({', '.join(str(v) for v in val)})" if len(val) == 3 else str(val)
    return str(val)


def generate_godot_project(
    project_path: str,
    project_name: str = "JarvisGame",
    description: str = "",
) -> str:
    """Generate a complete Godot 4 project with a basic 3D scene.

    Creates project.godot, a main scene with camera/light/floor/player,
    and a player controller script.
    """
    path = _ensure_project_dir(project_path)

    # project.godot
    project_cfg = dedent(f"""\
        ; Engine configuration file.
        ; Generated by Jarvis AI Agent.

        config_version=5

        [application]

        config/name="{project_name}"
        config/description="{description}"
        run/main_scene="res://main.tscn"
        config/features=PackedStringArray("4.3")

        [display]

        window/size/viewport_width=1280
        window/size/viewport_height=720

        [rendering]

        renderer/rendering_method="forward_plus"
    """)
    (path / "project.godot").write_text(project_cfg)

    # Main scene
    scene = SceneBuilder()
    floor_mesh = scene.add_sub_resource("BoxMesh", {"size": "Vector3(20, 0.1, 20)"})
    player_mesh = scene.add_sub_resource("CapsuleMesh", {"radius": 0.4, "height": 1.8})

    scene.add_node("Main", "Node3D")

    scene.add_node("Camera3D", "Camera3D", parent=".", properties={
        "transform": "Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 3, 8)",
        "rotation_degrees": "Vector3(-20, 0, 0)",
    })

    scene.add_node("DirectionalLight3D", "DirectionalLight3D", parent=".", properties={
        "transform": "Transform3D(1, 0, 0, 0, 0.7, 0.7, 0, -0.7, 0.7, 0, 10, 0)",
        "shadow_enabled": True,
    })

    scene.add_node("Floor", "MeshInstance3D", parent=".", properties={
        "mesh": f"SubResource(\"{floor_mesh}\")",
    })

    scene.add_node("Player", "CharacterBody3D", parent=".", properties={
        "transform": "Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0)",
        "script": 'ExtResource("1_player")',
    })

    scene.add_node("PlayerMesh", "MeshInstance3D", parent="Player", properties={
        "mesh": f"SubResource(\"{player_mesh}\")",
    })

    scene.add_node("CollisionShape3D", "CollisionShape3D", parent="Player", properties={
        "shape": "CapsuleShape3D",
    })

    # Write scene with ext_resource for player script
    tscn = scene.build()
    # Prepend ext_resource for the script
    tscn = tscn.replace(
        '[gd_scene load_steps=2 format=3]',
        '[gd_scene load_steps=3 format=3]\n\n'
        '[ext_resource type="Script" path="res://player.gd" id="1_player"]'
    )
    (path / "main.tscn").write_text(tscn)

    # Player script
    player = GDScriptBuilder("CharacterBody3D")
    player.add_export("speed", "float", "5.0")
    player.add_export("jump_strength", "float", "8.0")
    player.add_var("gravity", "ProjectSettings.get_setting(\"physics/3d/default_gravity\")")
    player.add_function("_physics_process", "delta", dedent("""\
        # Gravity
        if not is_on_floor():
        \tvelocity.y -= gravity * delta

        # Jump
        if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        \tvelocity.y = jump_strength

        # Movement
        var input_dir = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
        var direction = Vector3(input_dir.x, 0, input_dir.y).normalized()
        if direction:
        \tvelocity.x = direction.x * speed
        \tvelocity.z = direction.z * speed
        else:
        \tvelocity.x = move_toward(velocity.x, 0, speed)
        \tvelocity.z = move_toward(velocity.z, 0, speed)

        move_and_slide()"""))
    (path / "player.gd").write_text(player.build())

    files = list(path.glob("*"))
    return f"Created Godot 4 project at {path} with {len(files)} files: {[f.name for f in files]}"


def validate_godot_project(project_path: str) -> str:
    """Validate a Godot project using headless mode."""
    if not Path(_GODOT).exists():
        return f"Godot not found at {_GODOT}. Set GODOT_PATH env var."
    try:
        result = subprocess.run(
            [_GODOT, "--headless", "--path", project_path, "--quit"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return "Project validated successfully (no errors)."
        errors = result.stderr.strip()[:1000] if result.stderr else "Unknown error"
        return f"Validation issues:\n{errors}"
    except subprocess.TimeoutExpired:
        return "Validation timed out after 30s."
    except Exception as e:
        return f"Validation error: {e}"


def create_gdscript(
    file_path: str,
    extends: str = "Node",
    code: str = "",
) -> str:
    """Create a GDScript file with the given code."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"extends {extends}\n\n{code}\n"
    path.write_text(content)
    return f"Created GDScript at {path}"


def create_scene(
    file_path: str,
    scene_definition: str,
) -> str:
    """Create a .tscn scene file from raw definition."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scene_definition)
    return f"Created scene at {path}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="create_godot_project",
        description="Generate a complete Godot 4 project with 3D scene, camera, lights, floor, and player controller.",
        parameters={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path for the project directory"},
                "project_name": {"type": "string", "description": "Display name for the project"},
                "description": {"type": "string", "description": "Project description"},
            },
            "required": ["project_path"],
        },
        func=generate_godot_project,
    ))
    registry.register(ToolDef(
        name="validate_godot_project",
        description="Validate a Godot 4 project using headless mode. Checks for errors.",
        parameters={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to the Godot project"},
            },
            "required": ["project_path"],
        },
        func=validate_godot_project,
    ))
    registry.register(ToolDef(
        name="create_gdscript",
        description="Create a GDScript (.gd) file for Godot 4.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path for the .gd file"},
                "extends": {"type": "string", "description": "Base class to extend"},
                "code": {"type": "string", "description": "GDScript code body"},
            },
            "required": ["file_path"],
        },
        func=create_gdscript,
    ))
    registry.register(ToolDef(
        name="create_scene",
        description="Create a Godot 4 .tscn scene file.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path for the .tscn file"},
                "scene_definition": {"type": "string", "description": "Raw .tscn file content"},
            },
            "required": ["file_path", "scene_definition"],
        },
        func=create_scene,
    ))
