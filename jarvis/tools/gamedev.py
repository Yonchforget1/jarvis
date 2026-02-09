import os

from jarvis.tool_registry import ToolDef

# ============================================================================
# GAME TEMPLATES
# ============================================================================

PYGAME_MAIN_TEMPLATE = '''\
"""
{name}
{description}
"""
import pygame
import sys
import os

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TITLE = "{name}"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self):
        pass  # TODO: game logic

    def draw(self):
        self.screen.fill(BLACK)
        font = pygame.font.Font(None, 48)
        text = font.render(TITLE, True, WHITE)
        rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(text, rect)
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
'''

PYGAME_PLATFORMER_TEMPLATE = '''\
"""
{name} - Platformer
{description}
"""
import pygame
import sys

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15
MOVE_SPEED = 5

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (50, 100, 200)
GREEN = (50, 200, 50)


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((32, 48))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel_y = 0
        self.on_ground = False

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -MOVE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = MOVE_SPEED
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        self.vel_y += GRAVITY
        self.rect.x += dx
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if dx > 0:
                    self.rect.right = plat.rect.left
                elif dx < 0:
                    self.rect.left = plat.rect.right

        self.rect.y += int(self.vel_y)
        self.on_ground = False
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel_y > 0:
                    self.rect.bottom = plat.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = plat.rect.bottom
                    self.vel_y = 0


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(topleft=(x, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("{name}")
    clock = pygame.time.Clock()

    player = Player(100, 100)
    platforms = pygame.sprite.Group()
    platforms.add(Platform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40))
    platforms.add(Platform(200, 450, 150, 20))
    platforms.add(Platform(400, 350, 150, 20))
    platforms.add(Platform(100, 250, 150, 20))
    platforms.add(Platform(500, 200, 150, 20))

    all_sprites = pygame.sprite.Group(player, *platforms)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        player.update(platforms)
        screen.fill(BLACK)
        all_sprites.draw(screen)

        font = pygame.font.Font(None, 24)
        hud = font.render("Arrow keys / WASD to move, Space to jump", True, WHITE)
        screen.blit(hud, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
'''

PYGAME_SHOOTER_TEMPLATE = '''\
"""
{name} - Top-down Shooter
{description}
"""
import pygame
import sys
import math
import random

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
PLAYER_SPEED = 4
BULLET_SPEED = 8
ENEMY_SPEED = 2

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
YELLOW = (255, 255, 0)


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, GREEN, [(15, 0), (0, 30), (30, 30)])
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.health = 100
        self.score = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.rect.y -= PLAYER_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.rect.y += PLAYER_SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.rect.x += PLAYER_SPEED
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, target_x, target_y):
        super().__init__()
        self.image = pygame.Surface((6, 6))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(center=(x, y))
        angle = math.atan2(target_y - y, target_x - x)
        self.dx = math.cos(angle) * BULLET_SPEED
        self.dy = math.sin(angle) * BULLET_SPEED

    def update(self):
        self.rect.x += int(self.dx)
        self.rect.y += int(self.dy)
        if not pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT).colliderect(self.rect):
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((25, 25))
        self.image.fill(RED)
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top": self.rect = self.image.get_rect(center=(random.randint(0, SCREEN_WIDTH), -20))
        elif side == "bottom": self.rect = self.image.get_rect(center=(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 20))
        elif side == "left": self.rect = self.image.get_rect(center=(-20, random.randint(0, SCREEN_HEIGHT)))
        else: self.rect = self.image.get_rect(center=(SCREEN_WIDTH + 20, random.randint(0, SCREEN_HEIGHT)))

    def update(self, player_rect):
        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.centery - self.rect.centery
        dist = max(1, math.hypot(dx, dy))
        self.rect.x += int(dx / dist * ENEMY_SPEED)
        self.rect.y += int(dy / dist * ENEMY_SPEED)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("{name}")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    player = Player()
    bullets = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    spawn_timer = 0

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                bullets.add(Bullet(player.rect.centerx, player.rect.centery, mx, my))

        player.update()
        bullets.update()
        for e in enemies:
            e.update(player.rect)

        spawn_timer += 1
        if spawn_timer >= 60:
            enemies.add(Enemy())
            spawn_timer = 0

        for bullet in list(bullets):
            hit = pygame.sprite.spritecollideany(bullet, enemies)
            if hit:
                hit.kill()
                bullet.kill()
                player.score += 10

        if pygame.sprite.spritecollideany(player, enemies):
            player.health -= 1
            if player.health <= 0:
                running = False

        screen.fill(BLACK)
        screen.blit(player.image, player.rect)
        bullets.draw(screen)
        enemies.draw(screen)
        hud = font.render(f"HP: {{player.health}}  Score: {{player.score}}", True, WHITE)
        screen.blit(hud, (10, 10))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
'''

URSINA_FPS_TEMPLATE = '''\
"""
{name} - 3D First-Person
{description}
"""
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random

app = Ursina()

ground = Entity(model="plane", scale=(50, 1, 50), texture="grass", collider="box")

for i in range(10):
    Entity(
        model="cube",
        color=color.random_color(),
        scale=(2, 3, 2),
        position=(random.uniform(-20, 20), 1.5, random.uniform(-20, 20)),
        collider="box",
    )

Sky()
player = FirstPersonController()

def update():
    pass  # TODO: game logic

app.run()
'''

URSINA_THIRDPERSON_TEMPLATE = '''\
"""
{name} - 3D Third-Person
{description}
"""
from ursina import *
import random

app = Ursina()

ground = Entity(model="plane", scale=(50, 1, 50), texture="grass", collider="box")

player = Entity(model="cube", color=color.azure, scale=(1, 2, 1), position=(0, 1, 0), collider="box")
speed = 5

camera.position = (0, 10, -15)
camera.look_at(player)

Sky()

for i in range(10):
    Entity(
        model="cube",
        color=color.random_color(),
        scale=(2, 3, 2),
        position=(random.uniform(-20, 20), 1.5, random.uniform(-20, 20)),
        collider="box",
    )

def update():
    direction = Vec3(0, 0, 0)
    if held_keys["w"] or held_keys["up arrow"]: direction += Vec3(0, 0, 1)
    if held_keys["s"] or held_keys["down arrow"]: direction += Vec3(0, 0, -1)
    if held_keys["a"] or held_keys["left arrow"]: direction += Vec3(-1, 0, 0)
    if held_keys["d"] or held_keys["right arrow"]: direction += Vec3(1, 0, 0)

    if direction.length() > 0:
        direction = direction.normalized()
        player.position += direction * speed * time.dt

    camera.position = player.position + Vec3(0, 10, -15)
    camera.look_at(player)

app.run()
'''

TEMPLATES = {
    "pygame": {
        "default": PYGAME_MAIN_TEMPLATE,
        "platformer": PYGAME_PLATFORMER_TEMPLATE,
        "shooter": PYGAME_SHOOTER_TEMPLATE,
    },
    "ursina": {
        "default": URSINA_FPS_TEMPLATE,
        "fps": URSINA_FPS_TEMPLATE,
        "third_person": URSINA_THIRDPERSON_TEMPLATE,
    },
}

# ============================================================================
# TOOL FUNCTIONS
# ============================================================================


def create_game_project(
    name: str,
    engine: str = "pygame",
    template: str = "default",
    description: str = "",
) -> str:
    """Scaffold a complete game project."""
    engine = engine.lower()
    if engine not in TEMPLATES:
        return f"Error: Unsupported engine '{engine}'. Use 'pygame' or 'ursina'."

    template_key = template.lower()
    engine_templates = TEMPLATES[engine]
    if template_key not in engine_templates:
        available = ", ".join(engine_templates.keys())
        return f"Error: Unknown template '{template_key}' for {engine}. Available: {available}"

    project_dir = os.path.abspath(name)
    if os.path.exists(project_dir):
        return f"Error: Directory '{project_dir}' already exists."

    os.makedirs(project_dir)
    os.makedirs(os.path.join(project_dir, "assets", "sprites"))
    os.makedirs(os.path.join(project_dir, "assets", "sounds"))

    main_code = engine_templates[template_key].format(
        name=name, description=description or f"A {engine} game"
    )
    with open(os.path.join(project_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write(main_code)

    deps = {"pygame": "pygame", "ursina": "ursina"}
    with open(os.path.join(project_dir, "requirements.txt"), "w") as f:
        f.write(f"{deps[engine]}\n")

    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(f"# {name}\n\n{description or 'A game built with ' + engine}\n\n")
        f.write("## Setup\n```\npip install -r requirements.txt\npython main.py\n```\n")

    return (
        f"Created {engine} game project '{name}' at {project_dir}\n"
        f"Template: {template_key}\n"
        f"Structure:\n"
        f"  {name}/\n"
        f"    main.py\n"
        f"    requirements.txt\n"
        f"    README.md\n"
        f"    assets/sprites/\n"
        f"    assets/sounds/\n\n"
        f"Run: cd {project_dir} && pip install -r requirements.txt && python main.py"
    )


def generate_game_asset(
    description: str,
    asset_type: str = "sprite",
    width: int = 64,
    height: int = 64,
    output_path: str = "",
) -> str:
    """Generate a placeholder game asset image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "Error: Pillow is not installed. Run: pip install Pillow"

    asset_type = asset_type.lower()
    color_map = {
        "sprite": (50, 150, 250),
        "texture": (100, 180, 100),
        "background": (40, 40, 80),
        "icon": (250, 200, 50),
    }
    if asset_type not in color_map:
        return f"Error: Unknown asset_type '{asset_type}'. Use: sprite, texture, background, icon."

    bg_color = color_map[asset_type]
    img = Image.new("RGBA", (width, height), bg_color + (255,))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255, 200), width=2)

    label = description[:20] if len(description) > 20 else description
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text_bbox = draw.textbbox((0, 0), label, font=font) if font else (0, 0, width, 12)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    text_x = max(2, (width - text_w) // 2)
    text_y = max(2, (height - text_h) // 2)
    draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)
    draw.text((4, 4), asset_type.upper(), fill=(255, 255, 255, 128), font=font)

    if not output_path:
        output_path = f"{description.replace(' ', '_')[:30]}_{width}x{height}.png"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path)

    return f"Generated {asset_type} asset ({width}x{height}) saved to: {output_path}"


# ============================================================================
# REGISTRATION
# ============================================================================


def register(registry):
    registry.register(
        ToolDef(
            name="create_game_project",
            description=(
                "Scaffold a complete game project with directory structure, main.py, "
                "requirements.txt, and README. Engines: 'pygame' (2D) or 'ursina' (3D). "
                "Pygame templates: default, platformer, shooter. "
                "Ursina templates: default/fps, third_person."
            ),
            parameters={
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Project name (used as directory name).",
                    },
                    "engine": {
                        "type": "string",
                        "enum": ["pygame", "ursina"],
                        "description": "Game engine. Default: pygame.",
                        "default": "pygame",
                    },
                    "template": {
                        "type": "string",
                        "description": "Template: default, platformer, shooter (pygame); default, fps, third_person (ursina).",
                        "default": "default",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief game description.",
                        "default": "",
                    },
                },
                "required": ["name"],
            },
            func=create_game_project,
        )
    )
    registry.register(
        ToolDef(
            name="generate_game_asset",
            description=(
                "Generate a placeholder game asset image (colored rectangle with label). "
                "Types: sprite, texture, background, icon. Saves as PNG."
            ),
            parameters={
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the asset represents (used as label).",
                    },
                    "asset_type": {
                        "type": "string",
                        "enum": ["sprite", "texture", "background", "icon"],
                        "description": "Type of asset.",
                        "default": "sprite",
                    },
                    "width": {
                        "type": "integer",
                        "description": "Width in pixels.",
                        "default": 64,
                    },
                    "height": {
                        "type": "integer",
                        "description": "Height in pixels.",
                        "default": 64,
                    },
                    "output_path": {
                        "type": "string",
                        "description": "File path to save. Auto-generated if empty.",
                        "default": "",
                    },
                },
                "required": ["description"],
            },
            func=generate_game_asset,
        )
    )
