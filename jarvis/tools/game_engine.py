"""
Jarvis Game Engine Pipeline - Professional Godot 4 Project Generator

Generates complete, playable Godot 4 projects from game design specifications.
Outputs proper .tscn scene files, .gd scripts, project.godot configuration,
and all supporting resources. Projects can be opened directly in Godot 4.3+.
"""

import json
import os
import shutil
import subprocess
import textwrap
from dataclasses import dataclass, field
from typing import Any

from jarvis.tool_registry import ToolDef

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GODOT_PATH = os.environ.get("GODOT_PATH", r"C:\Godot\godot.exe")
GODOT_VERSION = 4  # Major version for compatibility checks


# ---------------------------------------------------------------------------
# Godot Resource ID Generator
# ---------------------------------------------------------------------------
class _IDGen:
    """Generates unique resource IDs for Godot scene files."""
    def __init__(self):
        self._ext = 0
        self._sub = 0

    def ext(self) -> int:
        self._ext += 1
        return self._ext

    def sub(self) -> int:
        self._sub += 1
        return self._sub


# ---------------------------------------------------------------------------
# Scene Tree Builder - Generates .tscn files
# ---------------------------------------------------------------------------
@dataclass
class GodotNode:
    """Represents a node in a Godot scene tree."""
    name: str
    type: str
    parent: str = ""  # "" for root, "." for direct child, "path/to" for nested
    properties: dict = field(default_factory=dict)
    script_path: str = ""  # res:// path to .gd script
    groups: list = field(default_factory=list)
    children: list = field(default_factory=list)


class SceneBuilder:
    """Builds Godot .tscn scene files programmatically."""

    def __init__(self):
        self._idgen = _IDGen()
        self._ext_resources: list[dict] = []
        self._sub_resources: list[dict] = []
        self._nodes: list[dict] = []

    def add_ext_resource(self, path: str, rtype: str) -> int:
        rid = self._idgen.ext()
        self._ext_resources.append({"path": path, "type": rtype, "id": rid})
        return rid

    def add_sub_resource(self, rtype: str, properties: dict = None) -> int:
        rid = self._idgen.sub()
        self._sub_resources.append({
            "type": rtype, "id": rid, "properties": properties or {}
        })
        return rid

    def add_node(self, name: str, node_type: str, parent: str = "",
                 properties: dict = None, script_id: int = None,
                 groups: list = None, instance_id: int = None):
        node = {"name": name, "type": node_type, "parent": parent}
        if properties:
            node["properties"] = properties
        if script_id is not None:
            node["script_id"] = script_id
        if groups:
            node["groups"] = groups
        if instance_id is not None:
            node["instance_id"] = instance_id
        self._nodes.append(node)

    def _format_value(self, val: Any) -> str:
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, int):
            return str(val)
        if isinstance(val, float):
            return str(val)
        if isinstance(val, str):
            if val.startswith("Vector") or val.startswith("Color") or \
               val.startswith("Transform") or val.startswith("Basis") or \
               val.startswith("NodePath") or val.startswith("SubResource") or \
               val.startswith("ExtResource") or val.startswith("Rect2") or \
               val.startswith("PackedScene") or val.startswith("AABB"):
                return val
            return f'"{val}"'
        if isinstance(val, list):
            inner = ", ".join(self._format_value(v) for v in val)
            return f"[{inner}]"
        if isinstance(val, dict):
            pairs = ", ".join(
                f'"{k}": {self._format_value(v)}' for k, v in val.items()
            )
            return "{" + pairs + "}"
        return str(val)

    def build(self, load_steps: int = None) -> str:
        lines = []
        if load_steps is None:
            load_steps = len(self._ext_resources) + len(self._sub_resources) + 1
        lines.append(
            f'[gd_scene load_steps={load_steps} format=3 uid="uid://generated"]'
        )
        lines.append("")

        for er in self._ext_resources:
            lines.append(
                f'[ext_resource type="{er["type"]}" path="{er["path"]}" id="{er["id"]}"]'
            )
        if self._ext_resources:
            lines.append("")

        for sr in self._sub_resources:
            lines.append(f'[sub_resource type="{sr["type"]}" id="{sr["id"]}"]')
            for k, v in sr["properties"].items():
                lines.append(f"{k} = {self._format_value(v)}")
            lines.append("")

        for i, node in enumerate(self._nodes):
            parts = [f'[node name="{node["name"]}"']
            if node["type"]:
                parts.append(f'type="{node["type"]}"')
            if i == 0:
                pass  # root node, no parent
            elif node.get("parent", ".") == ".":
                parts.append('parent="."')
            else:
                parts.append(f'parent="{node["parent"]}"')
            if node.get("instance_id"):
                parts.append(f'instance=ExtResource("{node["instance_id"]}")')
            if node.get("groups"):
                groups_str = ", ".join(f'"{g}"' for g in node["groups"])
                parts.append(f"groups=[{groups_str}]")
            lines.append(" ".join(parts) + "]")

            if node.get("script_id"):
                lines.append(f'script = ExtResource("{node["script_id"]}")')
            for k, v in node.get("properties", {}).items():
                lines.append(f"{k} = {self._format_value(v)}")
            lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# GDScript Generator
# ---------------------------------------------------------------------------
class GDScriptBuilder:
    """Generates GDScript source files."""

    def __init__(self, extends: str = "Node"):
        self._extends = extends
        self._class_name = ""
        self._signals: list[str] = []
        self._exports: list[str] = []
        self._vars: list[str] = []
        self._onready: list[str] = []
        self._funcs: list[tuple[str, str]] = []  # (signature, body)
        self._raw_blocks: list[str] = []

    def set_class_name(self, name: str):
        self._class_name = name
        return self

    def add_signal(self, sig: str):
        self._signals.append(sig)
        return self

    def add_export(self, line: str):
        self._exports.append(line)
        return self

    def add_var(self, line: str):
        self._vars.append(line)
        return self

    def add_onready(self, line: str):
        self._onready.append(line)
        return self

    def add_func(self, signature: str, body: str):
        self._funcs.append((signature, body))
        return self

    def add_raw(self, block: str):
        self._raw_blocks.append(block)
        return self

    def build(self) -> str:
        lines = [f"extends {self._extends}", ""]
        if self._class_name:
            lines.insert(1, f"class_name {self._class_name}")
            lines.insert(2, "")
        for s in self._signals:
            lines.append(f"signal {s}")
        if self._signals:
            lines.append("")
        for e in self._exports:
            lines.append(e)
        if self._exports:
            lines.append("")
        for v in self._vars:
            lines.append(v)
        if self._vars:
            lines.append("")
        for o in self._onready:
            lines.append(o)
        if self._onready:
            lines.append("")
        for raw in self._raw_blocks:
            lines.append(raw)
            lines.append("")
        for sig, body in self._funcs:
            lines.append(f"func {sig}:")
            for bline in body.split("\n"):
                lines.append(f"\t{bline}" if bline.strip() else "")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Project.godot Generator
# ---------------------------------------------------------------------------
def generate_project_godot(project_name: str, main_scene: str = "res://scenes/main.tscn",
                           input_actions: dict = None, autoloads: dict = None,
                           window_width: int = 1280, window_height: int = 720,
                           physics_fps: int = 60) -> str:
    """Generate a complete project.godot file."""
    lines = [
        '; Engine configuration file.',
        '; Generated by Jarvis Game Engine Pipeline.',
        '',
        'config_version=5',
        '',
        '[application]',
        '',
        f'config/name="{project_name}"',
        f'run/main_scene="{main_scene}"',
        'config/features=PackedStringArray("4.3", "Forward Plus")',
        '',
    ]

    # Autoloads
    if autoloads:
        lines.append('[autoload]')
        lines.append('')
        for name, path in autoloads.items():
            lines.append(f'{name}="*{path}"')
        lines.append('')

    # Display
    lines.extend([
        '[display]',
        '',
        f'window/size/viewport_width={window_width}',
        f'window/size/viewport_height={window_height}',
        'window/stretch/mode="canvas_items"',
        '',
    ])

    # Input mappings
    if input_actions:
        lines.append('[input]')
        lines.append('')
        for action_name, events in input_actions.items():
            event_list = []
            for ev in events:
                if ev.get("type") == "key":
                    keycode = ev["keycode"]
                    event_list.append(
                        f'Object(InputEventKey,"resource_local_to_scene":false,'
                        f'"resource_name":"","device":-1,"window_id":0,'
                        f'"alt_pressed":false,"shift_pressed":false,'
                        f'"ctrl_pressed":false,"meta_pressed":false,'
                        f'"pressed":false,"keycode":0,"physical_keycode":{keycode},'
                        f'"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)'
                    )
                elif ev.get("type") == "mouse_button":
                    event_list.append(
                        f'Object(InputEventMouseButton,"resource_local_to_scene":false,'
                        f'"resource_name":"","device":-1,"window_id":0,'
                        f'"alt_pressed":false,"shift_pressed":false,'
                        f'"ctrl_pressed":false,"meta_pressed":false,'
                        f'"button_mask":0,"position":Vector2(0,0),'
                        f'"global_position":Vector2(0,0),"factor":1.0,'
                        f'"button_index":{ev["button_index"]},"canceled":false,'
                        f'"pressed":true,"double_click":false,"script":null)'
                    )
            if event_list:
                ev_str = ", ".join(event_list)
                lines.append(
                    f'{action_name}={{"deadzone": 0.5, "events": [{ev_str}]}}'
                )
        lines.append('')

    # Physics
    lines.extend([
        '[physics]',
        '',
        f'common/physics_ticks_per_second={physics_fps}',
        '',
    ])

    # Rendering
    lines.extend([
        '[rendering]',
        '',
        'renderer/rendering_method="forward_plus"',
        'anti_aliasing/quality/msaa_3d=2',
        '',
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input Keycodes (Godot 4 key constants)
# ---------------------------------------------------------------------------
KEY = {
    "W": 4194439, "A": 4194429, "S": 4194451, "D": 4194432,
    "E": 4194433, "F": 4194434, "Q": 4194449, "R": 4194450,
    "I": 4194437, "SPACE": 4194306, "SHIFT": 4194325,
    "CTRL": 4194326, "ESCAPE": 4194305, "TAB": 4194306,
    "1": 4194353, "2": 4194354, "3": 4194355, "4": 4194356,
    "UP": 4194320, "DOWN": 4194322, "LEFT": 4194319, "RIGHT": 4194321,
}
MOUSE = {"LEFT": 1, "RIGHT": 2, "MIDDLE": 3}


# ---------------------------------------------------------------------------
# Standard Input Maps
# ---------------------------------------------------------------------------
def action_rpg_inputs() -> dict:
    """Standard input mapping for an action RPG."""
    return {
        "move_forward": [{"type": "key", "keycode": KEY["W"]}],
        "move_back": [{"type": "key", "keycode": KEY["S"]}],
        "move_left": [{"type": "key", "keycode": KEY["A"]}],
        "move_right": [{"type": "key", "keycode": KEY["D"]}],
        "attack": [{"type": "mouse_button", "button_index": MOUSE["LEFT"]}],
        "heavy_attack": [{"type": "mouse_button", "button_index": MOUSE["RIGHT"]}],
        "dodge": [{"type": "key", "keycode": KEY["SPACE"]}],
        "interact": [{"type": "key", "keycode": KEY["E"]}],
        "inventory": [{"type": "key", "keycode": KEY["I"]}],
        "pause": [{"type": "key", "keycode": KEY["ESCAPE"]}],
    }


# ---------------------------------------------------------------------------
# GDScript Templates - Game Systems
# ---------------------------------------------------------------------------

def _gdscript_game_manager() -> str:
    """Global game manager autoload."""
    return textwrap.dedent("""\
        extends Node

        ## Global game manager - handles state, score, and game flow.

        signal game_state_changed(new_state: String)
        signal player_died
        signal wave_completed(wave_number: int)
        signal boss_spawned

        enum GameState { MENU, PLAYING, PAUSED, GAME_OVER, VICTORY }

        var current_state: GameState = GameState.MENU
        var score: int = 0
        var current_wave: int = 0
        var enemies_alive: int = 0
        var player_ref: Node = null

        func change_state(new_state: GameState) -> void:
        \tvar old_state = current_state
        \tcurrent_state = new_state
        \tgame_state_changed.emit(GameState.keys()[new_state])
        \tmatch new_state:
        \t\tGameState.PLAYING:
        \t\t\tget_tree().paused = false
        \t\tGameState.PAUSED:
        \t\t\tget_tree().paused = true
        \t\tGameState.GAME_OVER:
        \t\t\tget_tree().paused = true

        func add_score(amount: int) -> void:
        \tscore += amount

        func register_enemy() -> void:
        \tenemies_alive += 1

        func enemy_killed() -> void:
        \tenemies_alive -= 1
        \tif enemies_alive <= 0:
        \t\twave_completed.emit(current_wave)

        func start_game() -> void:
        \tscore = 0
        \tcurrent_wave = 0
        \tenemies_alive = 0
        \tchange_state(GameState.PLAYING)

        func _input(event: InputEvent) -> void:
        \tif event.is_action_pressed("pause"):
        \t\tif current_state == GameState.PLAYING:
        \t\t\tchange_state(GameState.PAUSED)
        \t\telif current_state == GameState.PAUSED:
        \t\t\tchange_state(GameState.PLAYING)
    """)


def _gdscript_player_controller() -> str:
    """3D player character controller with combat."""
    return textwrap.dedent("""\
        extends CharacterBody3D

        ## Player controller with movement, combat, and dodge mechanics.

        signal health_changed(current: int, maximum: int)
        signal stamina_changed(current: float, maximum: float)
        signal died

        @export var move_speed: float = 7.0
        @export var sprint_speed: float = 12.0
        @export var jump_force: float = 8.0
        @export var gravity: float = 20.0
        @export var rotation_speed: float = 10.0
        @export var max_health: int = 100
        @export var max_stamina: float = 100.0
        @export var stamina_regen: float = 20.0
        @export var dodge_speed: float = 15.0
        @export var dodge_duration: float = 0.3
        @export var dodge_cooldown: float = 0.8
        @export var dodge_stamina_cost: float = 25.0
        @export var attack_damage: int = 20
        @export var heavy_attack_damage: int = 45
        @export var attack_range: float = 2.5

        var health: int
        var stamina: float
        var is_attacking: bool = false
        var is_dodging: bool = false
        var dodge_timer: float = 0.0
        var dodge_cooldown_timer: float = 0.0
        var dodge_direction: Vector3 = Vector3.ZERO
        var attack_cooldown: float = 0.0
        var is_invincible: bool = false
        var combo_count: int = 0
        var combo_timer: float = 0.0

        @onready var camera_pivot: Node3D = $CameraPivot
        @onready var attack_area: Area3D = $AttackArea
        @onready var mesh: MeshInstance3D = $Mesh
        @onready var anim_player: AnimationPlayer = $AnimationPlayer

        func _ready() -> void:
        \thealth = max_health
        \tstamina = max_stamina
        \thealth_changed.emit(health, max_health)
        \tstamina_changed.emit(stamina, max_stamina)
        \tif GameManager:
        \t\tGameManager.player_ref = self

        func _physics_process(delta: float) -> void:
        \t_handle_timers(delta)
        \t_handle_stamina_regen(delta)
        \t
        \tif is_dodging:
        \t\tvelocity = dodge_direction * dodge_speed
        \t\tvelocity.y -= gravity * delta
        \t\tmove_and_slide()
        \t\treturn
        \t
        \tif is_attacking:
        \t\tvelocity.x = 0
        \t\tvelocity.z = 0
        \t\tvelocity.y -= gravity * delta
        \t\tmove_and_slide()
        \t\treturn
        \t
        \t# Movement input
        \tvar input_dir := Vector3.ZERO
        \tif Input.is_action_pressed("move_forward"):
        \t\tinput_dir.z -= 1
        \tif Input.is_action_pressed("move_back"):
        \t\tinput_dir.z += 1
        \tif Input.is_action_pressed("move_left"):
        \t\tinput_dir.x -= 1
        \tif Input.is_action_pressed("move_right"):
        \t\tinput_dir.x += 1
        \t
        \t# Camera-relative movement
        \tif camera_pivot:
        \t\tvar cam_basis = camera_pivot.global_transform.basis
        \t\tvar forward = -cam_basis.z
        \t\tforward.y = 0
        \t\tforward = forward.normalized()
        \t\tvar right = cam_basis.x
        \t\tright.y = 0
        \t\tright = right.normalized()
        \t\tinput_dir = (forward * -input_dir.z + right * input_dir.x).normalized()
        \t
        \tvar speed = move_speed
        \tif input_dir.length() > 0.1:
        \t\tvar target_rotation = atan2(input_dir.x, input_dir.z)
        \t\trotation.y = lerp_angle(rotation.y, target_rotation, rotation_speed * delta)
        \t
        \tvelocity.x = input_dir.x * speed
        \tvelocity.z = input_dir.z * speed
        \t
        \t# Gravity
        \tif not is_on_floor():
        \t\tvelocity.y -= gravity * delta
        \telif Input.is_action_just_pressed("dodge") and velocity.y <= 0:
        \t\tvelocity.y = jump_force
        \t
        \tmove_and_slide()

        func _input(event: InputEvent) -> void:
        \tif event.is_action_pressed("attack") and not is_attacking and attack_cooldown <= 0:
        \t\t_perform_attack(attack_damage)
        \tif event.is_action_pressed("heavy_attack") and not is_attacking and attack_cooldown <= 0:
        \t\t_perform_heavy_attack()
        \tif event.is_action_pressed("dodge") and not is_dodging and dodge_cooldown_timer <= 0:
        \t\t_perform_dodge()

        func _perform_attack(damage: int) -> void:
        \tis_attacking = true
        \tattack_cooldown = 0.4
        \tcombo_count += 1
        \tcombo_timer = 0.8
        \t
        \t# Hit enemies in attack area
        \tvar bodies = attack_area.get_overlapping_bodies()
        \tfor body in bodies:
        \t\tif body.has_method("take_damage") and body != self:
        \t\t\tvar actual_damage = damage
        \t\t\tif combo_count >= 3:
        \t\t\t\tactual_damage = int(damage * 1.5)
        \t\t\t\tcombo_count = 0
        \t\t\tbody.take_damage(actual_damage, global_position)
        \t
        \tawait get_tree().create_timer(0.3).timeout
        \tis_attacking = false

        func _perform_heavy_attack() -> void:
        \tif stamina < 30.0:
        \t\treturn
        \tstamina -= 30.0
        \tstamina_changed.emit(stamina, max_stamina)
        \tis_attacking = true
        \tattack_cooldown = 0.8
        \t
        \tvar bodies = attack_area.get_overlapping_bodies()
        \tfor body in bodies:
        \t\tif body.has_method("take_damage") and body != self:
        \t\t\tbody.take_damage(heavy_attack_damage, global_position)
        \t
        \tawait get_tree().create_timer(0.5).timeout
        \tis_attacking = false

        func _perform_dodge() -> void:
        \tif stamina < dodge_stamina_cost:
        \t\treturn
        \tstamina -= dodge_stamina_cost
        \tstamina_changed.emit(stamina, max_stamina)
        \tis_dodging = true
        \tis_invincible = true
        \tdodge_timer = dodge_duration
        \tdodge_cooldown_timer = dodge_cooldown
        \t
        \t# Dodge in movement direction or backward
        \tvar input_dir = Vector3.ZERO
        \tif Input.is_action_pressed("move_forward"):
        \t\tinput_dir.z -= 1
        \tif Input.is_action_pressed("move_back"):
        \t\tinput_dir.z += 1
        \tif Input.is_action_pressed("move_left"):
        \t\tinput_dir.x -= 1
        \tif Input.is_action_pressed("move_right"):
        \t\tinput_dir.x += 1
        \tif input_dir.length() < 0.1:
        \t\tinput_dir = -global_transform.basis.z
        \tdodge_direction = input_dir.normalized()

        func _handle_timers(delta: float) -> void:
        \tif dodge_timer > 0:
        \t\tdodge_timer -= delta
        \t\tif dodge_timer <= 0:
        \t\t\tis_dodging = false
        \t\t\tis_invincible = false
        \tif dodge_cooldown_timer > 0:
        \t\tdodge_cooldown_timer -= delta
        \tif attack_cooldown > 0:
        \t\tattack_cooldown -= delta
        \tif combo_timer > 0:
        \t\tcombo_timer -= delta
        \t\tif combo_timer <= 0:
        \t\t\tcombo_count = 0

        func _handle_stamina_regen(delta: float) -> void:
        \tif stamina < max_stamina and not is_dodging and not is_attacking:
        \t\tstamina = min(max_stamina, stamina + stamina_regen * delta)
        \t\tstamina_changed.emit(stamina, max_stamina)

        func take_damage(amount: int, from_position: Vector3 = Vector3.ZERO) -> void:
        \tif is_invincible:
        \t\treturn
        \thealth -= amount
        \thealth_changed.emit(health, max_health)
        \t
        \t# Knockback
        \tif from_position != Vector3.ZERO:
        \t\tvar knockback = (global_position - from_position).normalized() * 5.0
        \t\tvelocity += knockback
        \t
        \tif health <= 0:
        \t\thealth = 0
        \t\tdied.emit()
        \t\tif GameManager:
        \t\t\tGameManager.change_state(GameManager.GameState.GAME_OVER)

        func heal(amount: int) -> void:
        \thealth = min(max_health, health + amount)
        \thealth_changed.emit(health, max_health)
    """)


def _gdscript_camera_controller() -> str:
    """Third-person camera with orbit and collision."""
    return textwrap.dedent("""\
        extends Node3D

        ## Third-person camera with orbit, zoom, and collision avoidance.

        @export var follow_speed: float = 8.0
        @export var rotation_speed: float = 0.003
        @export var min_pitch: float = -60.0
        @export var max_pitch: float = 40.0
        @export var default_distance: float = 8.0
        @export var min_distance: float = 2.0
        @export var max_distance: float = 15.0
        @export var zoom_speed: float = 2.0
        @export var collision_margin: float = 0.3

        var yaw: float = 0.0
        var pitch: float = -20.0
        var target_distance: float = 8.0

        @onready var camera: Camera3D = $Camera3D
        @onready var raycast: RayCast3D = $RayCast3D

        func _ready() -> void:
        \tInput.mouse_mode = Input.MOUSE_MODE_CAPTURED
        \ttarget_distance = default_distance

        func _unhandled_input(event: InputEvent) -> void:
        \tif event is InputEventMouseMotion:
        \t\tyaw -= event.relative.x * rotation_speed
        \t\tpitch -= event.relative.y * rotation_speed
        \t\tpitch = clamp(pitch, deg_to_rad(min_pitch), deg_to_rad(max_pitch))
        \t
        \tif event is InputEventMouseButton:
        \t\tif event.button_index == MOUSE_BUTTON_WHEEL_UP:
        \t\t\ttarget_distance = max(min_distance, target_distance - zoom_speed)
        \t\telif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
        \t\t\ttarget_distance = min(max_distance, target_distance + zoom_speed)

        func _physics_process(delta: float) -> void:
        \t# Update rotation
        \trotation = Vector3(pitch, yaw, 0)
        \t
        \t# Camera collision
        \tvar desired_pos = Vector3(0, 0, target_distance)
        \tif raycast:
        \t\traycast.target_position = Vector3(0, 0, target_distance)
        \t\traycast.force_raycast_update()
        \t\tif raycast.is_colliding():
        \t\t\tvar collision_point = raycast.get_collision_point()
        \t\t\tvar dist = global_position.distance_to(collision_point) - collision_margin
        \t\t\tdesired_pos.z = max(min_distance, dist)
        \t
        \tif camera:
        \t\tcamera.position = camera.position.lerp(desired_pos, follow_speed * delta)
    """)


def _gdscript_enemy_base() -> str:
    """Base enemy with AI state machine."""
    return textwrap.dedent("""\
        extends CharacterBody3D

        ## Base enemy with state machine AI, pathfinding, and combat.

        signal died(enemy: CharacterBody3D)

        enum State { IDLE, PATROL, CHASE, ATTACK, HURT, DEAD }

        @export var max_health: int = 50
        @export var move_speed: float = 4.0
        @export var chase_speed: float = 6.0
        @export var attack_damage: int = 15
        @export var attack_range: float = 2.0
        @export var detection_range: float = 15.0
        @export var attack_cooldown: float = 1.2
        @export var gravity: float = 20.0
        @export var score_value: int = 10
        @export var patrol_radius: float = 8.0
        @export var is_boss: bool = false

        var health: int
        var current_state: State = State.IDLE
        var player: Node3D = null
        var attack_timer: float = 0.0
        var spawn_position: Vector3
        var patrol_target: Vector3
        var hurt_timer: float = 0.0
        var nav_agent: NavigationAgent3D

        @onready var mesh: MeshInstance3D = $Mesh
        @onready var health_bar: Node = null

        func _ready() -> void:
        \thealth = max_health
        \tspawn_position = global_position
        \tpatrol_target = spawn_position
        \t
        \t# Find navigation agent
        \tfor child in get_children():
        \t\tif child is NavigationAgent3D:
        \t\t\tnav_agent = child
        \t\t\tbreak
        \t
        \tif not nav_agent:
        \t\tnav_agent = NavigationAgent3D.new()
        \t\tnav_agent.path_desired_distance = 1.0
        \t\tnav_agent.target_desired_distance = 1.5
        \t\tadd_child(nav_agent)
        \t
        \tif GameManager:
        \t\tGameManager.register_enemy()
        \t\tplayer = GameManager.player_ref

        func _physics_process(delta: float) -> void:
        \tif not is_on_floor():
        \t\tvelocity.y -= gravity * delta
        \t
        \tattack_timer -= delta
        \thurt_timer -= delta
        \t
        \tmatch current_state:
        \t\tState.IDLE:
        \t\t\t_state_idle(delta)
        \t\tState.PATROL:
        \t\t\t_state_patrol(delta)
        \t\tState.CHASE:
        \t\t\t_state_chase(delta)
        \t\tState.ATTACK:
        \t\t\t_state_attack(delta)
        \t\tState.HURT:
        \t\t\t_state_hurt(delta)
        \t\tState.DEAD:
        \t\t\treturn
        \t
        \tmove_and_slide()

        func _state_idle(delta: float) -> void:
        \tvelocity.x = 0
        \tvelocity.z = 0
        \tif _can_see_player():
        \t\tcurrent_state = State.CHASE
        \t\treturn
        \t# Start patrolling after idle
        \tvar random_offset = Vector3(randf_range(-patrol_radius, patrol_radius), 0, randf_range(-patrol_radius, patrol_radius))
        \tpatrol_target = spawn_position + random_offset
        \tcurrent_state = State.PATROL

        func _state_patrol(delta: float) -> void:
        \tif _can_see_player():
        \t\tcurrent_state = State.CHASE
        \t\treturn
        \t
        \tnav_agent.target_position = patrol_target
        \tif nav_agent.is_navigation_finished():
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \t
        \tvar next_pos = nav_agent.get_next_path_position()
        \tvar direction = (next_pos - global_position).normalized()
        \tdirection.y = 0
        \tvelocity.x = direction.x * move_speed
        \tvelocity.z = direction.z * move_speed
        \t
        \tif direction.length() > 0.1:
        \t\tvar target_rot = atan2(direction.x, direction.z)
        \t\trotation.y = lerp_angle(rotation.y, target_rot, 5.0 * delta)

        func _state_chase(delta: float) -> void:
        \tif not player or not is_instance_valid(player):
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \t
        \tvar dist = global_position.distance_to(player.global_position)
        \tif dist > detection_range * 1.5:
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \tif dist <= attack_range:
        \t\tcurrent_state = State.ATTACK
        \t\treturn
        \t
        \tnav_agent.target_position = player.global_position
        \tvar next_pos = nav_agent.get_next_path_position()
        \tvar direction = (next_pos - global_position).normalized()
        \tdirection.y = 0
        \tvelocity.x = direction.x * chase_speed
        \tvelocity.z = direction.z * chase_speed
        \t
        \tif direction.length() > 0.1:
        \t\tvar target_rot = atan2(direction.x, direction.z)
        \t\trotation.y = lerp_angle(rotation.y, target_rot, 8.0 * delta)

        func _state_attack(delta: float) -> void:
        \tvelocity.x = 0
        \tvelocity.z = 0
        \t
        \tif not player or not is_instance_valid(player):
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \t
        \tvar dist = global_position.distance_to(player.global_position)
        \tif dist > attack_range * 1.3:
        \t\tcurrent_state = State.CHASE
        \t\treturn
        \t
        \t# Face player
        \tvar dir_to_player = (player.global_position - global_position).normalized()
        \tvar target_rot = atan2(dir_to_player.x, dir_to_player.z)
        \trotation.y = lerp_angle(rotation.y, target_rot, 10.0 * delta)
        \t
        \tif attack_timer <= 0:
        \t\tattack_timer = attack_cooldown
        \t\tif player.has_method("take_damage"):
        \t\t\tplayer.take_damage(attack_damage, global_position)

        func _state_hurt(delta: float) -> void:
        \tif hurt_timer <= 0:
        \t\tif _can_see_player():
        \t\t\tcurrent_state = State.CHASE
        \t\telse:
        \t\t\tcurrent_state = State.IDLE

        func _can_see_player() -> bool:
        \tif not player or not is_instance_valid(player):
        \t\treturn false
        \treturn global_position.distance_to(player.global_position) <= detection_range

        func take_damage(amount: int, from_position: Vector3 = Vector3.ZERO) -> void:
        \thealth -= amount
        \t
        \t# Flash red
        \tif mesh and mesh.get_surface_override_material(0):
        \t\tvar mat = mesh.get_surface_override_material(0).duplicate()
        \t\tmat.albedo_color = Color.RED
        \t\tmesh.set_surface_override_material(0, mat)
        \t\tawait get_tree().create_timer(0.15).timeout
        \t\tif is_instance_valid(self) and mesh:
        \t\t\tvar orig_mat = StandardMaterial3D.new()
        \t\t\torig_mat.albedo_color = Color(0.8, 0.2, 0.2)
        \t\t\tmesh.set_surface_override_material(0, orig_mat)
        \t
        \tif health <= 0:
        \t\t_die()
        \t\treturn
        \t
        \thurt_timer = 0.3
        \tcurrent_state = State.HURT
        \t
        \t# Knockback
        \tif from_position != Vector3.ZERO:
        \t\tvar knockback = (global_position - from_position).normalized() * 3.0
        \t\tvelocity += knockback

        func _die() -> void:
        \tcurrent_state = State.DEAD
        \tdied.emit(self)
        \tif GameManager:
        \t\tGameManager.enemy_killed()
        \t\tGameManager.add_score(score_value)
        \t
        \t# Death animation - shrink and remove
        \tvar tween = create_tween()
        \ttween.tween_property(self, "scale", Vector3(0.1, 0.1, 0.1), 0.5)
        \ttween.tween_callback(queue_free)
    """)


def _gdscript_boss_enemy() -> str:
    """Boss enemy with multiple phases."""
    return textwrap.dedent("""\
        extends CharacterBody3D

        ## Boss enemy with multiple attack phases and special abilities.

        signal phase_changed(phase: int)
        signal boss_died
        signal health_changed(current: int, maximum: int)

        enum Phase { ONE, TWO, THREE }
        enum State { IDLE, CHASE, ATTACK, SPECIAL, SUMMON, HURT, DEAD }

        @export var max_health: int = 500
        @export var move_speed: float = 3.5
        @export var attack_damage: int = 25
        @export var attack_range: float = 3.5
        @export var detection_range: float = 30.0
        @export var gravity: float = 20.0
        @export var score_value: int = 500

        var health: int
        var current_phase: Phase = Phase.ONE
        var current_state: State = State.IDLE
        var player: Node3D = null
        var attack_timer: float = 0.0
        var special_timer: float = 5.0
        var summon_timer: float = 15.0
        var nav_agent: NavigationAgent3D

        @onready var mesh: MeshInstance3D = $Mesh

        func _ready() -> void:
        \thealth = max_health
        \thealth_changed.emit(health, max_health)
        \t
        \tfor child in get_children():
        \t\tif child is NavigationAgent3D:
        \t\t\tnav_agent = child
        \t\t\tbreak
        \tif not nav_agent:
        \t\tnav_agent = NavigationAgent3D.new()
        \t\tnav_agent.path_desired_distance = 1.5
        \t\tnav_agent.target_desired_distance = 2.0
        \t\tadd_child(nav_agent)
        \t
        \tif GameManager:
        \t\tGameManager.register_enemy()
        \t\tGameManager.boss_spawned.emit()
        \t\tplayer = GameManager.player_ref

        func _physics_process(delta: float) -> void:
        \tif not is_on_floor():
        \t\tvelocity.y -= gravity * delta
        \t
        \tattack_timer -= delta
        \tspecial_timer -= delta
        \tsummon_timer -= delta
        \t
        \t_check_phase()
        \t
        \tmatch current_state:
        \t\tState.IDLE:
        \t\t\t_state_idle(delta)
        \t\tState.CHASE:
        \t\t\t_state_chase(delta)
        \t\tState.ATTACK:
        \t\t\t_state_attack(delta)
        \t\tState.SPECIAL:
        \t\t\tpass  # Handled by timer
        \t\tState.DEAD:
        \t\t\treturn
        \t
        \tmove_and_slide()

        func _check_phase() -> void:
        \tvar health_pct = float(health) / float(max_health)
        \tvar new_phase = current_phase
        \tif health_pct <= 0.3:
        \t\tnew_phase = Phase.THREE
        \telif health_pct <= 0.6:
        \t\tnew_phase = Phase.TWO
        \t
        \tif new_phase != current_phase:
        \t\tcurrent_phase = new_phase
        \t\tphase_changed.emit(int(current_phase) + 1)
        \t\t_on_phase_change()

        func _on_phase_change() -> void:
        \t# Phase transition effect
        \tmatch current_phase:
        \t\tPhase.TWO:
        \t\t\tmove_speed = 5.0
        \t\t\tattack_damage = 35
        \t\t\t# Visual change
        \t\t\tif mesh:
        \t\t\t\tvar mat = StandardMaterial3D.new()
        \t\t\t\tmat.albedo_color = Color(1.0, 0.5, 0.0)
        \t\t\t\tmat.emission_enabled = true
        \t\t\t\tmat.emission = Color(1.0, 0.3, 0.0)
        \t\t\t\tmat.emission_energy_multiplier = 2.0
        \t\t\t\tmesh.set_surface_override_material(0, mat)
        \t\tPhase.THREE:
        \t\t\tmove_speed = 7.0
        \t\t\tattack_damage = 50
        \t\t\tattack_range = 4.5
        \t\t\tif mesh:
        \t\t\t\tvar mat = StandardMaterial3D.new()
        \t\t\t\tmat.albedo_color = Color(0.8, 0.0, 0.0)
        \t\t\t\tmat.emission_enabled = true
        \t\t\t\tmat.emission = Color(1.0, 0.0, 0.0)
        \t\t\t\tmat.emission_energy_multiplier = 4.0
        \t\t\t\tmesh.set_surface_override_material(0, mat)

        func _state_idle(delta: float) -> void:
        \tvelocity.x = 0
        \tvelocity.z = 0
        \tif player and is_instance_valid(player):
        \t\tif global_position.distance_to(player.global_position) <= detection_range:
        \t\t\tcurrent_state = State.CHASE

        func _state_chase(delta: float) -> void:
        \tif not player or not is_instance_valid(player):
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \t
        \tvar dist = global_position.distance_to(player.global_position)
        \t
        \t# Check for special attack
        \tif special_timer <= 0 and current_phase != Phase.ONE:
        \t\t_perform_special_attack()
        \t\treturn
        \t
        \tif dist <= attack_range:
        \t\tcurrent_state = State.ATTACK
        \t\treturn
        \t
        \tnav_agent.target_position = player.global_position
        \tvar next_pos = nav_agent.get_next_path_position()
        \tvar direction = (next_pos - global_position).normalized()
        \tdirection.y = 0
        \tvelocity.x = direction.x * move_speed
        \tvelocity.z = direction.z * move_speed
        \t
        \tif direction.length() > 0.1:
        \t\tvar target_rot = atan2(direction.x, direction.z)
        \t\trotation.y = lerp_angle(rotation.y, target_rot, 6.0 * delta)

        func _state_attack(delta: float) -> void:
        \tvelocity.x = 0
        \tvelocity.z = 0
        \t
        \tif not player or not is_instance_valid(player):
        \t\tcurrent_state = State.IDLE
        \t\treturn
        \t
        \tvar dist = global_position.distance_to(player.global_position)
        \tif dist > attack_range * 1.5:
        \t\tcurrent_state = State.CHASE
        \t\treturn
        \t
        \tvar dir_to_player = (player.global_position - global_position).normalized()
        \tvar target_rot = atan2(dir_to_player.x, dir_to_player.z)
        \trotation.y = lerp_angle(rotation.y, target_rot, 10.0 * delta)
        \t
        \tif attack_timer <= 0:
        \t\tattack_timer = 1.0 if current_phase == Phase.ONE else 0.6
        \t\tif player.has_method("take_damage"):
        \t\t\tplayer.take_damage(attack_damage, global_position)

        func _perform_special_attack() -> void:
        \tcurrent_state = State.SPECIAL
        \tspecial_timer = 8.0 if current_phase == Phase.TWO else 5.0
        \t
        \t# Ground slam - AOE damage
        \tif player and is_instance_valid(player):
        \t\tvar dist = global_position.distance_to(player.global_position)
        \t\tif dist < 8.0 and player.has_method("take_damage"):
        \t\t\tvar aoe_damage = attack_damage * 2
        \t\t\tplayer.take_damage(aoe_damage, global_position)
        \t
        \tawait get_tree().create_timer(1.0).timeout
        \tif is_instance_valid(self):
        \t\tcurrent_state = State.CHASE

        func take_damage(amount: int, from_position: Vector3 = Vector3.ZERO) -> void:
        \thealth -= amount
        \thealth_changed.emit(health, max_health)
        \t
        \tif mesh:
        \t\tvar mat = mesh.get_surface_override_material(0)
        \t\tif mat:
        \t\t\tvar old_color = mat.albedo_color
        \t\t\tmat.albedo_color = Color.WHITE
        \t\t\tawait get_tree().create_timer(0.1).timeout
        \t\t\tif is_instance_valid(self) and mesh and mesh.get_surface_override_material(0):
        \t\t\t\tmesh.get_surface_override_material(0).albedo_color = old_color
        \t
        \tif health <= 0:
        \t\t_die()

        func _die() -> void:
        \tcurrent_state = State.DEAD
        \tboss_died.emit()
        \tif GameManager:
        \t\tGameManager.enemy_killed()
        \t\tGameManager.add_score(score_value)
        \t\tGameManager.change_state(GameManager.GameState.VICTORY)
        \t
        \tvar tween = create_tween()
        \ttween.tween_property(self, "scale", Vector3(0.01, 0.01, 0.01), 1.5)
        \ttween.tween_callback(queue_free)
    """)


def _gdscript_wave_spawner() -> str:
    """Wave-based enemy spawner system."""
    return textwrap.dedent("""\
        extends Node3D

        ## Spawns waves of enemies with increasing difficulty, ending with a boss.

        signal wave_started(wave_number: int)
        signal all_waves_complete

        @export var enemy_scene_path: String = "res://scenes/enemy.tscn"
        @export var boss_scene_path: String = "res://scenes/boss.tscn"
        @export var total_waves: int = 5
        @export var base_enemies_per_wave: int = 3
        @export var enemies_increase_per_wave: int = 2
        @export var spawn_delay: float = 1.0
        @export var wave_delay: float = 3.0
        @export var spawn_radius: float = 15.0

        var current_wave: int = 0
        var spawning: bool = false

        func _ready() -> void:
        \tif GameManager:
        \t\tGameManager.wave_completed.connect(_on_wave_completed)

        func start_waves() -> void:
        \tcurrent_wave = 0
        \t_spawn_next_wave()

        func _spawn_next_wave() -> void:
        \tcurrent_wave += 1
        \tif GameManager:
        \t\tGameManager.current_wave = current_wave
        \t
        \tif current_wave > total_waves:
        \t\t_spawn_boss()
        \t\treturn
        \t
        \twave_started.emit(current_wave)
        \tspawning = true
        \t
        \tvar enemy_count = base_enemies_per_wave + (current_wave - 1) * enemies_increase_per_wave
        \tvar enemy_scene = load(enemy_scene_path)
        \tif not enemy_scene:
        \t\tpush_error("Cannot load enemy scene: " + enemy_scene_path)
        \t\treturn
        \t
        \tfor i in range(enemy_count):
        \t\tawait get_tree().create_timer(spawn_delay).timeout
        \t\tif not is_instance_valid(self):
        \t\t\treturn
        \t\tvar enemy = enemy_scene.instantiate()
        \t\tvar angle = randf() * TAU
        \t\tvar dist = randf_range(spawn_radius * 0.5, spawn_radius)
        \t\tenemy.global_position = global_position + Vector3(cos(angle) * dist, 0, sin(angle) * dist)
        \t\t
        \t\t# Scale difficulty with wave
        \t\tif enemy.has_method("set") and current_wave > 1:
        \t\t\tenemy.max_health = int(enemy.max_health * (1.0 + current_wave * 0.15))
        \t\t\tenemy.attack_damage = int(enemy.attack_damage * (1.0 + current_wave * 0.1))
        \t\t
        \t\tget_parent().add_child(enemy)
        \t
        \tspawning = false

        func _spawn_boss() -> void:
        \tvar boss_scene = load(boss_scene_path)
        \tif not boss_scene:
        \t\tpush_error("Cannot load boss scene: " + boss_scene_path)
        \t\treturn
        \t
        \tvar boss = boss_scene.instantiate()
        \tboss.global_position = global_position + Vector3(0, 0, -5)
        \tget_parent().add_child(boss)

        func _on_wave_completed(wave_number: int) -> void:
        \tif wave_number == current_wave and not spawning:
        \t\tawait get_tree().create_timer(wave_delay).timeout
        \t\tif is_instance_valid(self):
        \t\t\t_spawn_next_wave()
    """)


def _gdscript_hud() -> str:
    """Game HUD with health, stamina, score, wave info."""
    return textwrap.dedent("""\
        extends CanvasLayer

        ## Game HUD - health bar, stamina bar, score, wave counter, boss health.

        @onready var health_bar: ProgressBar = $MarginContainer/VBoxContainer/HealthBar
        @onready var stamina_bar: ProgressBar = $MarginContainer/VBoxContainer/StaminaBar
        @onready var score_label: Label = $MarginContainer/VBoxContainer/ScoreLabel
        @onready var wave_label: Label = $MarginContainer/VBoxContainer/WaveLabel
        @onready var boss_health_bar: ProgressBar = $BossHealthContainer/BossHealthBar
        @onready var boss_name_label: Label = $BossHealthContainer/BossNameLabel
        @onready var message_label: Label = $MessageLabel
        @onready var game_over_panel: Panel = $GameOverPanel

        var message_timer: float = 0.0

        func _ready() -> void:
        \tif boss_health_bar:
        \t\tboss_health_bar.visible = false
        \tif boss_name_label:
        \t\tboss_name_label.visible = false
        \tif game_over_panel:
        \t\tgame_over_panel.visible = false
        \tif message_label:
        \t\tmessage_label.text = ""
        \t
        \tif GameManager:
        \t\tGameManager.game_state_changed.connect(_on_game_state_changed)
        \t\tGameManager.wave_completed.connect(_on_wave_completed)
        \t\tGameManager.boss_spawned.connect(_on_boss_spawned)

        func _process(delta: float) -> void:
        \tif GameManager:
        \t\tif score_label:
        \t\t\tscore_label.text = "Score: " + str(GameManager.score)
        \t\tif wave_label:
        \t\t\twave_label.text = "Wave: " + str(GameManager.current_wave)
        \t
        \tif message_timer > 0:
        \t\tmessage_timer -= delta
        \t\tif message_timer <= 0 and message_label:
        \t\t\tmessage_label.text = ""

        func update_health(current: int, maximum: int) -> void:
        \tif health_bar:
        \t\thealth_bar.max_value = maximum
        \t\thealth_bar.value = current

        func update_stamina(current: float, maximum: float) -> void:
        \tif stamina_bar:
        \t\tstamina_bar.max_value = maximum
        \t\tstamina_bar.value = current

        func update_boss_health(current: int, maximum: int) -> void:
        \tif boss_health_bar:
        \t\tboss_health_bar.max_value = maximum
        \t\tboss_health_bar.value = current

        func show_message(text: String, duration: float = 3.0) -> void:
        \tif message_label:
        \t\tmessage_label.text = text
        \t\tmessage_timer = duration

        func _on_game_state_changed(new_state: String) -> void:
        \tif new_state == "GAME_OVER" and game_over_panel:
        \t\tgame_over_panel.visible = true
        \t\tInput.mouse_mode = Input.MOUSE_MODE_VISIBLE
        \telif new_state == "VICTORY" and game_over_panel:
        \t\tgame_over_panel.visible = true
        \t\tInput.mouse_mode = Input.MOUSE_MODE_VISIBLE
        \t\tif message_label:
        \t\t\tmessage_label.text = "VICTORY!"

        func _on_wave_completed(wave_number: int) -> void:
        \tshow_message("Wave " + str(wave_number) + " Complete!", 2.0)

        func _on_boss_spawned() -> void:
        \tshow_message("BOSS INCOMING!", 3.0)
        \tif boss_health_bar:
        \t\tboss_health_bar.visible = true
        \tif boss_name_label:
        \t\tboss_name_label.visible = true
    """)


def _gdscript_save_system() -> str:
    """Save/load system using JSON."""
    return textwrap.dedent("""\
        extends Node

        ## Save/load game state to JSON files.

        const SAVE_DIR = "user://saves/"
        const SAVE_FILE = "savegame.json"

        func _ready() -> void:
        \tDirAccess.make_dir_recursive_absolute(SAVE_DIR)

        func save_game() -> bool:
        \tvar save_data = {}
        \t
        \t# Save game state
        \tif GameManager:
        \t\tsave_data["score"] = GameManager.score
        \t\tsave_data["wave"] = GameManager.current_wave
        \t
        \t# Save player state
        \tif GameManager and GameManager.player_ref and is_instance_valid(GameManager.player_ref):
        \t\tvar p = GameManager.player_ref
        \t\tsave_data["player"] = {
        \t\t\t"health": p.health,
        \t\t\t"max_health": p.max_health,
        \t\t\t"position": {"x": p.global_position.x, "y": p.global_position.y, "z": p.global_position.z},
        \t\t}
        \t
        \tvar json_string = JSON.stringify(save_data, "  ")
        \tvar file = FileAccess.open(SAVE_DIR + SAVE_FILE, FileAccess.WRITE)
        \tif not file:
        \t\tpush_error("Could not open save file for writing")
        \t\treturn false
        \tfile.store_string(json_string)
        \tfile.close()
        \treturn true

        func load_game() -> Dictionary:
        \tvar path = SAVE_DIR + SAVE_FILE
        \tif not FileAccess.file_exists(path):
        \t\treturn {}
        \t
        \tvar file = FileAccess.open(path, FileAccess.READ)
        \tif not file:
        \t\treturn {}
        \t
        \tvar json_string = file.get_as_text()
        \tfile.close()
        \t
        \tvar json = JSON.new()
        \tvar result = json.parse(json_string)
        \tif result != OK:
        \t\tpush_error("Failed to parse save file")
        \t\treturn {}
        \t
        \treturn json.data

        func has_save() -> bool:
        \treturn FileAccess.file_exists(SAVE_DIR + SAVE_FILE)

        func delete_save() -> void:
        \tvar path = SAVE_DIR + SAVE_FILE
        \tif FileAccess.file_exists(path):
        \t\tDirAccess.remove_absolute(path)
    """)


def _gdscript_audio_manager() -> str:
    """Audio manager with buses and pooling."""
    return textwrap.dedent("""\
        extends Node

        ## Audio manager with sound pooling and bus control.

        var sfx_players: Array[AudioStreamPlayer] = []
        var music_player: AudioStreamPlayer = null
        const MAX_SFX_PLAYERS = 16

        func _ready() -> void:
        \t# Create music player
        \tmusic_player = AudioStreamPlayer.new()
        \tmusic_player.bus = "Music" if AudioServer.get_bus_index("Music") >= 0 else "Master"
        \tadd_child(music_player)
        \t
        \t# Create SFX pool
        \tfor i in range(MAX_SFX_PLAYERS):
        \t\tvar player = AudioStreamPlayer.new()
        \t\tplayer.bus = "SFX" if AudioServer.get_bus_index("SFX") >= 0 else "Master"
        \t\tadd_child(player)
        \t\tsfx_players.append(player)

        func play_sfx(stream: AudioStream, volume_db: float = 0.0) -> void:
        \tif not stream:
        \t\treturn
        \tfor player in sfx_players:
        \t\tif not player.playing:
        \t\t\tplayer.stream = stream
        \t\t\tplayer.volume_db = volume_db
        \t\t\tplayer.play()
        \t\t\treturn
        \t# All busy - steal oldest
        \tsfx_players[0].stream = stream
        \tsfx_players[0].volume_db = volume_db
        \tsfx_players[0].play()

        func play_music(stream: AudioStream, volume_db: float = -5.0, fade_in: float = 1.0) -> void:
        \tif not stream:
        \t\treturn
        \tif music_player.playing:
        \t\tvar tween = create_tween()
        \t\ttween.tween_property(music_player, "volume_db", -40.0, 0.5)
        \t\tawait tween.finished
        \t
        \tmusic_player.stream = stream
        \tmusic_player.volume_db = -40.0
        \tmusic_player.play()
        \t
        \tvar tween = create_tween()
        \ttween.tween_property(music_player, "volume_db", volume_db, fade_in)

        func stop_music(fade_out: float = 1.0) -> void:
        \tif music_player.playing:
        \t\tvar tween = create_tween()
        \t\ttween.tween_property(music_player, "volume_db", -40.0, fade_out)
        \t\tawait tween.finished
        \t\tmusic_player.stop()

        func set_master_volume(linear: float) -> void:
        \tAudioServer.set_bus_volume_db(0, linear_to_db(linear))

        func set_sfx_volume(linear: float) -> void:
        \tvar idx = AudioServer.get_bus_index("SFX")
        \tif idx >= 0:
        \t\tAudioServer.set_bus_volume_db(idx, linear_to_db(linear))

        func set_music_volume(linear: float) -> void:
        \tvar idx = AudioServer.get_bus_index("Music")
        \tif idx >= 0:
        \t\tAudioServer.set_bus_volume_db(idx, linear_to_db(linear))
    """)


def _gdscript_inventory_system() -> str:
    """Inventory system with items."""
    return textwrap.dedent("""\
        extends Node

        ## Inventory system with item stacking, equipment slots, and consumables.

        signal inventory_changed
        signal item_used(item_id: String)
        signal item_equipped(item_id: String, slot: String)

        const MAX_SLOTS: int = 20

        var items: Array[Dictionary] = []
        var equipment: Dictionary = {
        \t"weapon": null,
        \t"armor": null,
        \t"accessory": null,
        }

        # Item database
        var item_db: Dictionary = {
        \t"health_potion": {
        \t\t"name": "Health Potion",
        \t\t"type": "consumable",
        \t\t"description": "Restores 50 HP",
        \t\t"max_stack": 10,
        \t\t"heal_amount": 50,
        \t},
        \t"iron_sword": {
        \t\t"name": "Iron Sword",
        \t\t"type": "weapon",
        \t\t"description": "A sturdy iron sword. +10 ATK",
        \t\t"max_stack": 1,
        \t\t"attack_bonus": 10,
        \t},
        \t"leather_armor": {
        \t\t"name": "Leather Armor",
        \t\t"type": "armor",
        \t\t"description": "Basic protection. +15 DEF",
        \t\t"max_stack": 1,
        \t\t"defense_bonus": 15,
        \t},
        \t"speed_ring": {
        \t\t"name": "Speed Ring",
        \t\t"type": "accessory",
        \t\t"description": "Increases move speed by 20%",
        \t\t"max_stack": 1,
        \t\t"speed_bonus": 0.2,
        \t},
        }

        func add_item(item_id: String, amount: int = 1) -> bool:
        \tif item_id not in item_db:
        \t\treturn false
        \t
        \tvar template = item_db[item_id]
        \t
        \t# Try to stack with existing
        \tfor item in items:
        \t\tif item["id"] == item_id and item["count"] < template["max_stack"]:
        \t\t\tvar can_add = min(amount, template["max_stack"] - item["count"])
        \t\t\titem["count"] += can_add
        \t\t\tamount -= can_add
        \t\t\tif amount <= 0:
        \t\t\t\tinventory_changed.emit()
        \t\t\t\treturn true
        \t
        \t# Add new stacks
        \twhile amount > 0 and items.size() < MAX_SLOTS:
        \t\tvar stack_size = min(amount, template["max_stack"])
        \t\titems.append({"id": item_id, "count": stack_size})
        \t\tamount -= stack_size
        \t
        \tinventory_changed.emit()
        \treturn amount <= 0

        func remove_item(item_id: String, amount: int = 1) -> bool:
        \tvar remaining = amount
        \tfor i in range(items.size() - 1, -1, -1):
        \t\tif items[i]["id"] == item_id:
        \t\t\tvar can_remove = min(remaining, items[i]["count"])
        \t\t\titems[i]["count"] -= can_remove
        \t\t\tremaining -= can_remove
        \t\t\tif items[i]["count"] <= 0:
        \t\t\t\titems.remove_at(i)
        \t\t\tif remaining <= 0:
        \t\t\t\tinventory_changed.emit()
        \t\t\t\treturn true
        \tinventory_changed.emit()
        \treturn false

        func use_item(item_id: String) -> void:
        \tif item_id not in item_db:
        \t\treturn
        \tvar template = item_db[item_id]
        \t
        \tmatch template["type"]:
        \t\t"consumable":
        \t\t\tif has_item(item_id):
        \t\t\t\tremove_item(item_id)
        \t\t\t\titem_used.emit(item_id)
        \t\t\t\t# Apply effect
        \t\t\t\tif template.has("heal_amount") and GameManager and GameManager.player_ref:
        \t\t\t\t\tGameManager.player_ref.heal(template["heal_amount"])
        \t\t"weapon", "armor", "accessory":
        \t\t\tequip_item(item_id)

        func equip_item(item_id: String) -> void:
        \tif item_id not in item_db:
        \t\treturn
        \tvar template = item_db[item_id]
        \tvar slot = template["type"]
        \tif slot not in equipment:
        \t\treturn
        \t
        \t# Unequip current
        \tif equipment[slot] != null:
        \t\tadd_item(equipment[slot])
        \t
        \tif has_item(item_id):
        \t\tremove_item(item_id)
        \t\tequipment[slot] = item_id
        \t\titem_equipped.emit(item_id, slot)
        \t\tinventory_changed.emit()

        func has_item(item_id: String, amount: int = 1) -> bool:
        \tvar total = 0
        \tfor item in items:
        \t\tif item["id"] == item_id:
        \t\t\ttotal += item["count"]
        \treturn total >= amount

        func get_item_count(item_id: String) -> int:
        \tvar total = 0
        \tfor item in items:
        \t\tif item["id"] == item_id:
        \t\t\ttotal += item["count"]
        \treturn total
    """)


def _gdscript_dialogue_system() -> str:
    """Branching dialogue system."""
    return textwrap.dedent("""\
        extends CanvasLayer

        ## Dialogue system with branching choices and NPC conversations.

        signal dialogue_started
        signal dialogue_ended
        signal choice_made(choice_index: int)

        @onready var dialogue_panel: Panel = $DialoguePanel
        @onready var speaker_label: Label = $DialoguePanel/SpeakerLabel
        @onready var text_label: RichTextLabel = $DialoguePanel/TextLabel
        @onready var choices_container: VBoxContainer = $DialoguePanel/ChoicesContainer
        @onready var continue_label: Label = $DialoguePanel/ContinueLabel

        var dialogue_data: Array = []
        var current_index: int = 0
        var is_active: bool = false
        var typing_speed: float = 0.03
        var is_typing: bool = false

        func _ready() -> void:
        \tif dialogue_panel:
        \t\tdialogue_panel.visible = false
        \tprocess_mode = Node.PROCESS_MODE_ALWAYS

        func _input(event: InputEvent) -> void:
        \tif not is_active:
        \t\treturn
        \tif event.is_action_pressed("interact") or (event is InputEventMouseButton and event.pressed):
        \t\tif is_typing:
        \t\t\t_skip_typing()
        \t\telse:
        \t\t\t_advance_dialogue()

        func start_dialogue(data: Array) -> void:
        \tdialogue_data = data
        \tcurrent_index = 0
        \tis_active = true
        \tif dialogue_panel:
        \t\tdialogue_panel.visible = true
        \tdialogue_started.emit()
        \t_show_current_line()

        func _show_current_line() -> void:
        \tif current_index >= dialogue_data.size():
        \t\tend_dialogue()
        \t\treturn
        \t
        \tvar line = dialogue_data[current_index]
        \t
        \tif speaker_label:
        \t\tspeaker_label.text = line.get("speaker", "")
        \t
        \t# Clear choices
        \tif choices_container:
        \t\tfor child in choices_container.get_children():
        \t\t\tchild.queue_free()
        \t
        \tif continue_label:
        \t\tcontinue_label.visible = false
        \t
        \t# Type out text
        \tif text_label:
        \t\ttext_label.text = ""
        \t\tis_typing = true
        \t\tvar full_text = line.get("text", "")
        \t\tfor i in range(full_text.length()):
        \t\t\tif not is_typing:
        \t\t\t\tbreak
        \t\t\ttext_label.text += full_text[i]
        \t\t\tawait get_tree().create_timer(typing_speed).timeout
        \t\ttext_label.text = full_text
        \t\tis_typing = false
        \t
        \t# Show choices or continue prompt
        \tif line.has("choices") and choices_container:
        \t\tfor i in range(line["choices"].size()):
        \t\t\tvar choice = line["choices"][i]
        \t\t\tvar btn = Button.new()
        \t\t\tbtn.text = choice.get("text", "...")
        \t\t\tvar idx = i
        \t\t\tvar next = choice.get("next", current_index + 1)
        \t\t\tbtn.pressed.connect(func(): _select_choice(idx, next))
        \t\t\tchoices_container.add_child(btn)
        \telif continue_label:
        \t\tcontinue_label.visible = true

        func _skip_typing() -> void:
        \tis_typing = false

        func _advance_dialogue() -> void:
        \tvar line = dialogue_data[current_index]
        \tif line.has("choices"):
        \t\treturn  # Must select a choice
        \tcurrent_index = line.get("next", current_index + 1)
        \t_show_current_line()

        func _select_choice(index: int, next_index: int) -> void:
        \tchoice_made.emit(index)
        \tcurrent_index = next_index
        \t_show_current_line()

        func end_dialogue() -> void:
        \tis_active = false
        \tif dialogue_panel:
        \t\tdialogue_panel.visible = false
        \tdialogue_ended.emit()
    """)


def _gdscript_main_scene() -> str:
    """Main game scene controller."""
    return textwrap.dedent("""\
        extends Node3D

        ## Main scene - sets up the game world and starts wave spawning.

        @onready var player: CharacterBody3D = $Player
        @onready var hud: CanvasLayer = $HUD
        @onready var wave_spawner: Node3D = $WaveSpawner

        func _ready() -> void:
        \tif GameManager:
        \t\tGameManager.start_game()
        \t
        \t# Connect player signals to HUD
        \tif player and hud:
        \t\tif player.has_signal("health_changed"):
        \t\t\tplayer.health_changed.connect(hud.update_health)
        \t\tif player.has_signal("stamina_changed"):
        \t\t\tplayer.stamina_changed.connect(hud.update_stamina)
        \t
        \t# Start waves after short delay
        \tawait get_tree().create_timer(2.0).timeout
        \tif wave_spawner and wave_spawner.has_method("start_waves"):
        \t\twave_spawner.start_waves()
    """)


# ---------------------------------------------------------------------------
# Scene Builders - Create .tscn files for each game element
# ---------------------------------------------------------------------------

def build_player_scene() -> str:
    """Build the player character .tscn scene."""
    sb = SceneBuilder()

    # Script
    script_id = sb.add_ext_resource("res://scripts/player_controller.gd", "Script")
    camera_script_id = sb.add_ext_resource("res://scripts/camera_controller.gd", "Script")

    # Player mesh material
    player_mat_id = sb.add_sub_resource("StandardMaterial3D", {
        "albedo_color": "Color(0.2, 0.4, 0.9, 1.0)",
    })

    # Player capsule mesh
    player_mesh_id = sb.add_sub_resource("CapsuleMesh", {
        "radius": 0.4,
        "height": 1.8,
        "material": f'SubResource("{player_mat_id}")',
    })

    # Attack area collision shape
    attack_shape_id = sb.add_sub_resource("SphereShape3D", {
        "radius": 2.5,
    })

    # Root - CharacterBody3D
    sb.add_node("Player", "CharacterBody3D", properties={
        "collision_layer": 1,
        "collision_mask": 3,
    }, script_id=script_id)

    # Collision shape
    capsule_id = sb.add_sub_resource("CapsuleShape3D", {
        "radius": 0.4,
        "height": 1.8,
    })
    sb.add_node("CollisionShape3D", "CollisionShape3D", parent=".",
                properties={"shape": f'SubResource("{capsule_id}")',
                            "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, 0)'})

    # Player mesh (capsule visual)
    sb.add_node("Mesh", "MeshInstance3D", parent=".",
                properties={
                    "mesh": f'SubResource("{player_mesh_id}")',
                    "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, 0)',
                })

    # Camera pivot
    sb.add_node("CameraPivot", "Node3D", parent=".",
                properties={"transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.5, 0)'},
                script_id=camera_script_id)

    # Camera
    sb.add_node("Camera3D", "Camera3D", parent="CameraPivot",
                properties={
                    "transform": 'Transform3D(1, 0, 0, 0, 0.94, 0.34, 0, -0.34, 0.94, 0, 2, 8)',
                    "fov": 70.0,
                })

    # Camera raycast for collision
    sb.add_node("RayCast3D", "RayCast3D", parent="CameraPivot",
                properties={
                    "target_position": "Vector3(0, 0, 8)",
                    "collision_mask": 4,
                })

    # Attack area
    sb.add_node("AttackArea", "Area3D", parent=".",
                properties={
                    "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.9, -1.5)',
                    "collision_layer": 0,
                    "collision_mask": 2,
                })
    sb.add_node("AttackShape", "CollisionShape3D", parent="AttackArea",
                properties={"shape": f'SubResource("{attack_shape_id}")'})

    # Animation player (placeholder)
    sb.add_node("AnimationPlayer", "AnimationPlayer", parent=".")

    return sb.build()


def build_enemy_scene() -> str:
    """Build a standard enemy .tscn scene."""
    sb = SceneBuilder()

    script_id = sb.add_ext_resource("res://scripts/enemy_base.gd", "Script")

    enemy_mat_id = sb.add_sub_resource("StandardMaterial3D", {
        "albedo_color": "Color(0.8, 0.2, 0.2, 1.0)",
    })

    enemy_mesh_id = sb.add_sub_resource("CapsuleMesh", {
        "radius": 0.4,
        "height": 1.6,
        "material": f'SubResource("{enemy_mat_id}")',
    })

    capsule_id = sb.add_sub_resource("CapsuleShape3D", {
        "radius": 0.4,
        "height": 1.6,
    })

    sb.add_node("Enemy", "CharacterBody3D", properties={
        "collision_layer": 2,
        "collision_mask": 1,
    }, script_id=script_id)

    sb.add_node("CollisionShape3D", "CollisionShape3D", parent=".",
                properties={"shape": f'SubResource("{capsule_id}")',
                            "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.8, 0)'})

    sb.add_node("Mesh", "MeshInstance3D", parent=".",
                properties={
                    "mesh": f'SubResource("{enemy_mesh_id}")',
                    "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.8, 0)',
                })

    sb.add_node("NavigationAgent3D", "NavigationAgent3D", parent=".",
                properties={
                    "path_desired_distance": 1.0,
                    "target_desired_distance": 1.5,
                })

    return sb.build()


def build_boss_scene() -> str:
    """Build the boss enemy .tscn scene."""
    sb = SceneBuilder()

    script_id = sb.add_ext_resource("res://scripts/boss_enemy.gd", "Script")

    boss_mat_id = sb.add_sub_resource("StandardMaterial3D", {
        "albedo_color": "Color(0.6, 0.0, 0.6, 1.0)",
        "emission_enabled": True,
        "emission": "Color(0.5, 0.0, 0.5, 1.0)",
        "emission_energy_multiplier": 1.5,
    })

    boss_mesh_id = sb.add_sub_resource("CapsuleMesh", {
        "radius": 0.8,
        "height": 3.0,
        "material": f'SubResource("{boss_mat_id}")',
    })

    capsule_id = sb.add_sub_resource("CapsuleShape3D", {
        "radius": 0.8,
        "height": 3.0,
    })

    sb.add_node("Boss", "CharacterBody3D", properties={
        "collision_layer": 2,
        "collision_mask": 1,
        "transform": 'Transform3D(2, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0)',
    }, script_id=script_id)

    sb.add_node("CollisionShape3D", "CollisionShape3D", parent=".",
                properties={"shape": f'SubResource("{capsule_id}")',
                            "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.5, 0)'})

    sb.add_node("Mesh", "MeshInstance3D", parent=".",
                properties={
                    "mesh": f'SubResource("{boss_mesh_id}")',
                    "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.5, 0)',
                })

    sb.add_node("NavigationAgent3D", "NavigationAgent3D", parent=".",
                properties={
                    "path_desired_distance": 1.5,
                    "target_desired_distance": 2.0,
                })

    return sb.build()


def build_hud_scene() -> str:
    """Build the HUD .tscn scene."""
    sb = SceneBuilder()

    script_id = sb.add_ext_resource("res://scripts/hud.gd", "Script")

    # Health bar style
    health_style_id = sb.add_sub_resource("StyleBoxFlat", {
        "bg_color": "Color(0.8, 0.1, 0.1, 1.0)",
        "corner_radius_top_left": 4,
        "corner_radius_top_right": 4,
        "corner_radius_bottom_left": 4,
        "corner_radius_bottom_right": 4,
    })
    health_bg_id = sb.add_sub_resource("StyleBoxFlat", {
        "bg_color": "Color(0.2, 0.2, 0.2, 0.8)",
        "corner_radius_top_left": 4,
        "corner_radius_top_right": 4,
        "corner_radius_bottom_left": 4,
        "corner_radius_bottom_right": 4,
    })

    # Stamina bar style
    stamina_style_id = sb.add_sub_resource("StyleBoxFlat", {
        "bg_color": "Color(0.2, 0.7, 0.2, 1.0)",
        "corner_radius_top_left": 4,
        "corner_radius_top_right": 4,
        "corner_radius_bottom_left": 4,
        "corner_radius_bottom_right": 4,
    })

    # Boss health style
    boss_style_id = sb.add_sub_resource("StyleBoxFlat", {
        "bg_color": "Color(0.8, 0.0, 0.8, 1.0)",
        "corner_radius_top_left": 4,
        "corner_radius_top_right": 4,
        "corner_radius_bottom_left": 4,
        "corner_radius_bottom_right": 4,
    })

    sb.add_node("HUD", "CanvasLayer", script_id=script_id)

    # Main HUD container
    sb.add_node("MarginContainer", "MarginContainer", parent=".",
                properties={
                    "anchors_preset": 0,
                    "offset_left": 10.0,
                    "offset_top": 10.0,
                    "offset_right": 310.0,
                    "offset_bottom": 120.0,
                })

    sb.add_node("VBoxContainer", "VBoxContainer", parent="MarginContainer")

    sb.add_node("HealthBar", "ProgressBar", parent="MarginContainer/VBoxContainer",
                properties={
                    "custom_minimum_size": "Vector2(280, 25)",
                    "max_value": 100.0,
                    "value": 100.0,
                    "show_percentage": False,
                })

    sb.add_node("StaminaBar", "ProgressBar", parent="MarginContainer/VBoxContainer",
                properties={
                    "custom_minimum_size": "Vector2(280, 20)",
                    "max_value": 100.0,
                    "value": 100.0,
                    "show_percentage": False,
                })

    sb.add_node("ScoreLabel", "Label", parent="MarginContainer/VBoxContainer",
                properties={"text": '"Score: 0"'})

    sb.add_node("WaveLabel", "Label", parent="MarginContainer/VBoxContainer",
                properties={"text": '"Wave: 0"'})

    # Boss health (top center)
    sb.add_node("BossHealthContainer", "VBoxContainer", parent=".",
                properties={
                    "anchors_preset": 5,
                    "anchor_left": 0.5,
                    "anchor_right": 0.5,
                    "offset_left": -200.0,
                    "offset_top": 20.0,
                    "offset_right": 200.0,
                    "offset_bottom": 80.0,
                })

    sb.add_node("BossNameLabel", "Label", parent="BossHealthContainer",
                properties={
                    "text": '"BOSS"',
                    "horizontal_alignment": 1,
                })

    sb.add_node("BossHealthBar", "ProgressBar", parent="BossHealthContainer",
                properties={
                    "custom_minimum_size": "Vector2(400, 30)",
                    "max_value": 500.0,
                    "value": 500.0,
                    "show_percentage": False,
                })

    # Center message
    sb.add_node("MessageLabel", "Label", parent=".",
                properties={
                    "anchors_preset": 8,
                    "anchor_left": 0.5,
                    "anchor_top": 0.3,
                    "anchor_right": 0.5,
                    "anchor_bottom": 0.3,
                    "offset_left": -200.0,
                    "offset_right": 200.0,
                    "text": '""',
                    "horizontal_alignment": 1,
                })

    # Game over panel
    sb.add_node("GameOverPanel", "Panel", parent=".",
                properties={
                    "anchors_preset": 15,
                    "anchor_right": 1.0,
                    "anchor_bottom": 1.0,
                    "visible": False,
                })

    sb.add_node("GameOverLabel", "Label", parent="GameOverPanel",
                properties={
                    "anchors_preset": 8,
                    "anchor_left": 0.5,
                    "anchor_top": 0.4,
                    "anchor_right": 0.5,
                    "anchor_bottom": 0.4,
                    "offset_left": -150.0,
                    "offset_right": 150.0,
                    "text": '"GAME OVER"',
                    "horizontal_alignment": 1,
                })

    return sb.build()


def build_main_scene() -> str:
    """Build the main game world .tscn scene."""
    sb = SceneBuilder()

    main_script_id = sb.add_ext_resource("res://scripts/main_scene.gd", "Script")
    player_scene_id = sb.add_ext_resource("res://scenes/player.tscn", "PackedScene")
    hud_scene_id = sb.add_ext_resource("res://scenes/hud.tscn", "PackedScene")
    wave_script_id = sb.add_ext_resource("res://scripts/wave_spawner.gd", "Script")

    # Environment
    env_id = sb.add_sub_resource("Environment", {
        "background_mode": 1,
        "background_color": "Color(0.15, 0.15, 0.25, 1.0)",
        "ambient_light_source": 2,
        "ambient_light_color": "Color(0.3, 0.3, 0.4, 1.0)",
        "ambient_light_energy": 0.5,
        "tonemap_mode": 2,
        "ssao_enabled": True,
    })

    # Ground material
    ground_mat_id = sb.add_sub_resource("StandardMaterial3D", {
        "albedo_color": "Color(0.3, 0.35, 0.3, 1.0)",
    })

    # Navigation mesh
    nav_mesh_id = sb.add_sub_resource("NavigationMesh", {
        "vertices": "PackedVector3Array(-30, 0, -30, -30, 0, 30, 30, 0, 30, 30, 0, -30)",
        "polygons": '[PackedInt32Array(0, 1, 2, 3)]',
    })

    # Root
    sb.add_node("Main", "Node3D", script_id=main_script_id)

    # World environment
    sb.add_node("WorldEnvironment", "WorldEnvironment", parent=".",
                properties={"environment": f'SubResource("{env_id}")'})

    # Directional light (sun)
    sb.add_node("DirectionalLight3D", "DirectionalLight3D", parent=".",
                properties={
                    "transform": 'Transform3D(0.87, -0.32, 0.38, 0, 0.77, 0.64, -0.5, -0.56, 0.67, 0, 15, 0)',
                    "light_color": "Color(1.0, 0.95, 0.85, 1.0)",
                    "light_energy": 1.2,
                    "shadow_enabled": True,
                })

    # Ground plane mesh
    ground_mesh_id = sb.add_sub_resource("PlaneMesh", {
        "size": "Vector2(60, 60)",
        "material": f'SubResource("{ground_mat_id}")',
    })

    sb.add_node("Ground", "StaticBody3D", parent=".",
                properties={"collision_layer": 4, "collision_mask": 0})

    sb.add_node("GroundMesh", "MeshInstance3D", parent="Ground",
                properties={
                    "mesh": f'SubResource("{ground_mesh_id}")',
                })

    ground_col_id = sb.add_sub_resource("BoxShape3D", {
        "size": "Vector3(60, 0.1, 60)",
    })
    sb.add_node("GroundCollision", "CollisionShape3D", parent="Ground",
                properties={
                    "shape": f'SubResource("{ground_col_id}")',
                    "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.05, 0)',
                })

    # Navigation region
    sb.add_node("NavigationRegion3D", "NavigationRegion3D", parent=".",
                properties={"navigation_mesh": f'SubResource("{nav_mesh_id}")'})

    # Player (instanced scene)
    sb.add_node("Player", "", parent=".",
                properties={"transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0)'},
                instance_id=player_scene_id)

    # HUD (instanced scene)
    sb.add_node("HUD", "", parent=".", instance_id=hud_scene_id)

    # Wave spawner
    sb.add_node("WaveSpawner", "Node3D", parent=".",
                properties={"transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0)'},
                script_id=wave_script_id)

    # Arena walls (invisible collision)
    for name, pos in [("WallN", "0,2,30"), ("WallS", "0,2,-30"),
                      ("WallE", "30,2,0"), ("WallW", "-30,2,0")]:
        sb.add_node(name, "StaticBody3D", parent=".",
                    properties={
                        "collision_layer": 4,
                        "transform": f'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {pos})',
                    })
        wall_shape_id = sb.add_sub_resource("BoxShape3D", {
            "size": "Vector3(60, 4, 1)" if "N" in name or "S" in name else "Vector3(1, 4, 60)",
        })
        sb.add_node(f"{name}Col", "CollisionShape3D", parent=name,
                    properties={"shape": f'SubResource("{wall_shape_id}")'})

    # Decorative pillars
    pillar_mat_id = sb.add_sub_resource("StandardMaterial3D", {
        "albedo_color": "Color(0.5, 0.5, 0.55, 1.0)",
    })
    pillar_mesh_id = sb.add_sub_resource("BoxMesh", {
        "size": "Vector3(2, 4, 2)",
        "material": f'SubResource("{pillar_mat_id}")',
    })
    pillar_positions = [(-10, 0, -10), (10, 0, -10), (-10, 0, 10), (10, 0, 10),
                        (-20, 0, 0), (20, 0, 0), (0, 0, -20), (0, 0, 20)]
    for i, (px, py, pz) in enumerate(pillar_positions):
        pname = f"Pillar{i}"
        sb.add_node(pname, "StaticBody3D", parent=".",
                    properties={
                        "collision_layer": 4,
                        "transform": f'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {px}, {py}, {pz})',
                    })
        sb.add_node(f"{pname}Mesh", "MeshInstance3D", parent=pname,
                    properties={
                        "mesh": f'SubResource("{pillar_mesh_id}")',
                        "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0)',
                    })
        pillar_col_id = sb.add_sub_resource("BoxShape3D", {
            "size": "Vector3(2, 4, 2)",
        })
        sb.add_node(f"{pname}Col", "CollisionShape3D", parent=pname,
                    properties={
                        "shape": f'SubResource("{pillar_col_id}")',
                        "transform": 'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 0)',
                    })

    # Torches / point lights for atmosphere
    light_positions = [(-15, 4, -15), (15, 4, -15), (-15, 4, 15), (15, 4, 15)]
    for i, (lx, ly, lz) in enumerate(light_positions):
        sb.add_node(f"Light{i}", "OmniLight3D", parent=".",
                    properties={
                        "transform": f'Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, {lx}, {ly}, {lz})',
                        "light_color": "Color(1.0, 0.7, 0.3, 1.0)",
                        "light_energy": 2.0,
                        "omni_range": 10.0,
                        "shadow_enabled": True,
                    })

    return sb.build()


# ---------------------------------------------------------------------------
# Master Project Generator
# ---------------------------------------------------------------------------

def generate_godot_project(
    project_name: str,
    output_dir: str = "",
    game_type: str = "action_rpg",
    description: str = "",
) -> str:
    """Generate a complete Godot 4 project with all game systems.

    Args:
        project_name: Name of the game project.
        output_dir: Where to create the project. Defaults to current directory.
        game_type: Type of game to generate (action_rpg, etc).
        description: Game description for documentation.

    Returns:
        Status message with project path.
    """
    if not output_dir:
        output_dir = os.getcwd()

    project_path = os.path.join(output_dir, project_name)

    if os.path.exists(project_path):
        return f"Error: Directory '{project_path}' already exists."

    try:
        # Create directory structure
        dirs = [
            "scenes", "scripts", "assets/models", "assets/textures",
            "assets/audio/sfx", "assets/audio/music", "assets/fonts",
            "resources", "addons",
        ]
        for d in dirs:
            os.makedirs(os.path.join(project_path, d), exist_ok=True)

        # Generate project.godot
        inputs = action_rpg_inputs() if game_type == "action_rpg" else {}
        autoloads = {
            "GameManager": "res://scripts/game_manager.gd",
            "SaveSystem": "res://scripts/save_system.gd",
            "AudioManager": "res://scripts/audio_manager.gd",
            "Inventory": "res://scripts/inventory_system.gd",
        }
        project_godot = generate_project_godot(
            project_name=project_name,
            main_scene="res://scenes/main.tscn",
            input_actions=inputs,
            autoloads=autoloads,
        )
        _write(project_path, "project.godot", project_godot)

        # Generate all GDScript files
        scripts = {
            "scripts/game_manager.gd": _gdscript_game_manager(),
            "scripts/player_controller.gd": _gdscript_player_controller(),
            "scripts/camera_controller.gd": _gdscript_camera_controller(),
            "scripts/enemy_base.gd": _gdscript_enemy_base(),
            "scripts/boss_enemy.gd": _gdscript_boss_enemy(),
            "scripts/wave_spawner.gd": _gdscript_wave_spawner(),
            "scripts/hud.gd": _gdscript_hud(),
            "scripts/save_system.gd": _gdscript_save_system(),
            "scripts/audio_manager.gd": _gdscript_audio_manager(),
            "scripts/inventory_system.gd": _gdscript_inventory_system(),
            "scripts/dialogue_system.gd": _gdscript_dialogue_system(),
            "scripts/main_scene.gd": _gdscript_main_scene(),
        }
        for path, content in scripts.items():
            _write(project_path, path, content)

        # Generate scene files
        scenes = {
            "scenes/player.tscn": build_player_scene(),
            "scenes/enemy.tscn": build_enemy_scene(),
            "scenes/boss.tscn": build_boss_scene(),
            "scenes/hud.tscn": build_hud_scene(),
            "scenes/main.tscn": build_main_scene(),
        }
        for path, content in scenes.items():
            _write(project_path, path, content)

        # Generate default bus layout
        _write(project_path, "default_bus_layout.tres", _default_bus_layout())

        # Generate .godot directory marker
        _write(project_path, ".godot/editor_settings.txt",
               "# Jarvis-generated project\n")

        file_count = len(scripts) + len(scenes) + 2
        return (
            f"Generated Godot 4 project '{project_name}' at {project_path}\n"
            f"Type: {game_type}\n"
            f"Files created: {file_count}\n"
            f"Scenes: {', '.join(scenes.keys())}\n"
            f"Scripts: {len(scripts)} GDScript files\n"
            f"Systems: GameManager, Combat, Enemy AI, Boss, Wave Spawner, "
            f"HUD, Save/Load, Audio, Inventory, Dialogue\n\n"
            f"To open: {GODOT_PATH} --path {project_path} --editor"
        )
    except Exception as e:
        # Cleanup on failure
        if os.path.exists(project_path):
            shutil.rmtree(project_path, ignore_errors=True)
        return f"Error generating project: {e}"


def _write(base: str, rel_path: str, content: str) -> None:
    """Write a file, creating parent directories as needed."""
    full = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def _default_bus_layout() -> str:
    """Godot audio bus layout with Master, Music, and SFX buses."""
    return textwrap.dedent("""\
        [gd_resource type="AudioBusLayout" format=3]

        [resource]
        bus/1/name = &"Music"
        bus/1/solo = false
        bus/1/mute = false
        bus/1/bypass_fx = false
        bus/1/volume_db = 0.0
        bus/1/send = &"Master"
        bus/2/name = &"SFX"
        bus/2/solo = false
        bus/2/mute = false
        bus/2/bypass_fx = false
        bus/2/volume_db = 0.0
        bus/2/send = &"Master"
    """)


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------

def register(registry):
    """Register game engine tools with the Jarvis tool registry."""
    registry.register(
        ToolDef(
            name="create_godot_project",
            description=(
                "Generate a complete, playable Godot 4 game project. "
                "Creates all scene files (.tscn), GDScript files (.gd), "
                "project configuration, and game systems including: "
                "player controller, enemy AI, boss fights, wave spawner, "
                "combat system, HUD, save/load, audio management, "
                "inventory, and dialogue. Output can be opened directly in Godot 4.3+."
            ),
            parameters={
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Name of the game project (used as directory name).",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to create project in. Defaults to current directory.",
                        "default": "",
                    },
                    "game_type": {
                        "type": "string",
                        "enum": ["action_rpg"],
                        "description": "Type of game to generate.",
                        "default": "action_rpg",
                    },
                    "description": {
                        "type": "string",
                        "description": "Game description.",
                        "default": "",
                    },
                },
                "required": ["project_name"],
            },
            func=generate_godot_project,
        )
    )
