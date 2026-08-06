#!/usr/bin/env python3
"""Generate SpineSpy's retro pixel-art posture pets.

Sprites are authored on a small logical grid (48x56 -- the aspect ratio of the
96x112 floating pet view) using explicit pixel loops, so every edge stays hard
and no anti-aliasing creeps in. Export upscales with nearest-neighbour sampling
so the pixel grid survives on retina displays.

Run:  poetry run python scripts/generate_pet_sprites.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

WIDTH, HEIGHT = 48, 56
SCALE = 4
TRANSPARENT = (0, 0, 0, 0)

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets" / "pets"

# Muted 16-bit palettes: one outline, one base tone, one shadow tone per region.
OTTER_PALETTE = {
    "line": (43, 32, 27, 255),
    "fur": (129, 97, 68, 255),
    "fur_shade": (96, 70, 50, 255),
    "cream": (234, 222, 196, 255),
    "cream_shade": (198, 182, 154, 255),
    "mask": (186, 160, 128, 255),
    "shine": (247, 242, 232, 255),
}

SHRIMP_PALETTE = {
    "line": (61, 33, 26, 255),
    "shell": (198, 108, 79, 255),
    "shell_shade": (156, 77, 55, 255),
    "fin": (172, 88, 62, 255),
    "fin_shade": (134, 66, 46, 255),
    "whisker": (176, 118, 96, 255),
    "shine": (232, 176, 146, 255),
}


def new_grid() -> list[list[str | None]]:
    return [[None] * WIDTH for _ in range(HEIGHT)]


def fill_ellipse(grid, cx, cy, rx, ry, key, only=None) -> None:
    """Fill a hard-edged ellipse. `only` clips painting to existing keys."""
    for y in range(max(0, cy - ry), min(HEIGHT, cy + ry + 1)):
        for x in range(max(0, cx - rx), min(WIDTH, cx + rx + 1)):
            nx = (x - cx) / (rx + 0.5)
            ny = (y - cy) / (ry + 0.5)
            if nx * nx + ny * ny > 1.0:
                continue
            if only is not None and grid[y][x] not in only:
                continue
            grid[y][x] = key


def fill_rect(grid, x0, y0, x1, y1, key, only=None) -> None:
    for y in range(max(0, y0), min(HEIGHT, y1 + 1)):
        for x in range(max(0, x0), min(WIDTH, x1 + 1)):
            if only is not None and grid[y][x] not in only:
                continue
            grid[y][x] = key


def _line_points(x0, y0, x1, y1):
    """Bresenham, so diagonals stay single-pixel clean."""
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        err2 = err * 2
        if err2 > -dy:
            err -= dy
            x0 += sx
        if err2 < dx:
            err += dx
            y0 += sy


def draw_polyline(grid, points, key, only=None) -> None:
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        for x, y in _line_points(x0, y0, x1, y1):
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
                continue
            if only is not None and grid[y][x] not in only:
                continue
            grid[y][x] = key


def add_shadow(grid, pairs, offset=(2, 2)) -> None:
    """Two-tone shading: darken the band hugging the bottom-right silhouette.

    Light reads as coming from the top-left. A pixel becomes its shadow tone
    when sampling away from the light leaves the silhouette entirely.
    """
    dx, dy = offset
    targets = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            key = grid[y][x]
            if key not in pairs:
                continue
            nx, ny = x + dx, y + dy
            outside = not (0 <= nx < WIDTH and 0 <= ny < HEIGHT) or grid[ny][nx] is None
            if outside:
                targets.append((x, y, pairs[key]))
    for x, y, key in targets:
        grid[y][x] = key


def add_outline(grid, key="line") -> None:
    """Wrap the silhouette in a 1px dark outline, growing outward."""
    edges = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] is not None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT and grid[ny][nx] is not None:
                    edges.append((x, y))
                    break
    for x, y in edges:
        grid[y][x] = key


def to_image(grid, palette, scale=SCALE) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), TRANSPARENT)
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            key = grid[y][x]
            if key is not None:
                pixels[x, y] = palette[key]
    return image.resize((WIDTH * scale, HEIGHT * scale), Image.NEAREST)


def build_otter() -> list[list[str | None]]:
    """Upright chibi otter, slight top-down view: good posture."""
    grid = new_grid()

    # Body, haunches and thick tail sweeping to the right.
    fill_ellipse(grid, 24, 38, 11, 12, "fur")
    fill_ellipse(grid, 16, 48, 5, 4, "fur")
    fill_ellipse(grid, 32, 48, 5, 4, "fur")
    for x, y, r in ((34, 44, 5), (38, 46, 4), (42, 47, 3)):
        fill_ellipse(grid, x, y, r, r, "fur")

    # Cream chest.
    fill_ellipse(grid, 24, 41, 7, 9, "cream")

    # Oversized head with ears cresting the top.
    fill_ellipse(grid, 24, 18, 13, 12, "fur")
    for ear_x in (12, 36):
        fill_ellipse(grid, ear_x, 10, 4, 4, "fur")
        fill_ellipse(grid, ear_x, 10, 2, 2, "mask")

    # Cream face, then the darker tan bandit mask across the eye line, then
    # the cream muzzle punched back out below it.
    fill_ellipse(grid, 24, 20, 10, 9, "cream")
    fill_ellipse(grid, 24, 19, 11, 4, "mask", only=("cream",))
    fill_ellipse(grid, 24, 24, 6, 4, "cream", only=("cream", "mask"))

    add_shadow(grid, {"fur": "fur_shade", "cream": "cream_shade"})

    # Outlined cream feet and paws read against the fur instead of blending in.
    for foot_x in (15, 33):
        fill_ellipse(grid, foot_x, 49, 5, 4, "line")
        fill_ellipse(grid, foot_x, 49, 4, 3, "cream")
    for paw_x in (17, 31):
        fill_ellipse(grid, paw_x, 34, 4, 4, "line")
        fill_ellipse(grid, paw_x, 34, 3, 3, "cream")

    # Face details sit on top of shading so they stay crisp.
    for eye_x in (16, 30):
        fill_rect(grid, eye_x, 17, eye_x + 2, 20, "line")
        fill_rect(grid, eye_x, 17, eye_x, 17, "shine")
    fill_rect(grid, 23, 24, 25, 25, "line")
    draw_polyline(grid, [(21, 27), (23, 28), (24, 27), (25, 28), (27, 27)], "line")

    add_outline(grid)
    return grid


def build_shrimp() -> list[list[str | None]]:
    """Curled chibi shrimp, side view: slouching posture."""
    grid = new_grid()

    # Segmented body as a tapering C-curve, back arcing up and over.
    spine = (
        (13, 25, 7),
        (18, 21, 8),
        (25, 20, 8),
        (31, 23, 7),
        (35, 28, 7),
        (37, 34, 6),
        (36, 40, 5),
        (32, 44, 5),
        (28, 47, 4),
    )
    for x, y, r in spine:
        fill_ellipse(grid, x, y, r, r, "shell")

    # Pointed rostrum at the head.
    fill_ellipse(grid, 9, 23, 4, 2, "fin")
    fill_ellipse(grid, 5, 22, 2, 1, "fin")

    add_shadow(grid, {"shell": "shell_shade", "fin": "fin_shade"})

    # Highlight streak along the back.
    draw_polyline(
        grid,
        [(20, 14), (27, 14), (32, 18)],
        "shine",
        only=("shell", "shell_shade"),
    )

    # Shell segment ridges, drawn perpendicular to the curve.
    for (x0, y0, _), (x1, y1, r1) in zip(spine[3:6], spine[4:7]):
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        tx, ty = x1 - x0, y1 - y0
        span = max(abs(tx), abs(ty)) or 1
        nx, ny = -ty / span, tx / span
        reach = r1 - 1
        draw_polyline(
            grid,
            [
                (round(mx - nx * reach), round(my - ny * reach)),
                (round(mx + nx * reach), round(my + ny * reach)),
            ],
            "shell_shade",
            only=("shell", "shell_shade", "shine"),
        )

    # Outlined tail fan so it separates from the body instead of merging.
    fill_ellipse(grid, 24, 50, 6, 4, "line")
    fill_ellipse(grid, 24, 50, 5, 3, "fin")
    fill_ellipse(grid, 18, 51, 4, 3, "line")
    fill_ellipse(grid, 18, 51, 3, 2, "fin")

    # Big chibi eye with a single-pixel highlight.
    fill_ellipse(grid, 14, 22, 3, 3, "line")
    fill_rect(grid, 13, 21, 13, 21, "shine")

    add_outline(grid)

    # Legs and antennae are hairlines drawn after the outline pass so they stay
    # a single pixel wide. They may cross the outline so they stay attached.
    for x0, y0 in ((19, 29), (23, 31), (27, 33), (30, 37)):
        draw_polyline(
            grid,
            [(x0, y0), (x0 - 2, y0 + 4)],
            "fin_shade",
            only=(None, "line"),
        )
    draw_polyline(
        grid,
        [(8, 20), (5, 13), (12, 6), (26, 3), (38, 6)],
        "whisker",
        only=(None,),
    )
    draw_polyline(
        grid,
        [(8, 22), (4, 17), (10, 10), (24, 7), (40, 11)],
        "whisker",
        only=(None,),
    )
    return grid


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder, palette in (
        ("posture-good.png", build_otter, OTTER_PALETTE),
        ("posture-bad.png", build_shrimp, SHRIMP_PALETTE),
    ):
        image = to_image(builder(), palette)
        destination = ASSET_DIR / filename
        image.save(destination)
        print(f"wrote {destination} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
