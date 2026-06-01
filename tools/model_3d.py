"""
3D Model Generation — generate basic 3D models and export as OBJ/STL.
"""
import json
import math
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


def _generate_cube(size: float = 1.0) -> str:
    s = size / 2
    vertices = [
        (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
        (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s),
    ]
    faces = [
        (1, 2, 3, 4), (5, 8, 7, 6), (1, 5, 6, 2),
        (2, 6, 7, 3), (3, 7, 8, 4), (5, 1, 4, 8),
    ]
    lines = ["# NexusMind Generated Cube"]
    for v in vertices:
        lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
    for f in faces:
        lines.append(f"f {' '.join(str(i) for i in f)}")
    return "\n".join(lines)


def _generate_sphere(radius: float = 1.0, segments: int = 16, rings: int = 12) -> str:
    lines = ["# NexusMind Generated Sphere"]
    vertices = []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            vertices.append((x, y, z))
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")

    for i in range(rings):
        for j in range(segments):
            a = i * segments + j + 1
            b = i * segments + (j + 1) % segments + 1
            c = (i + 1) * segments + (j + 1) % segments + 1
            d = (i + 1) * segments + j + 1
            lines.append(f"f {a} {b} {c} {d}")

    return "\n".join(lines)


def _generate_cylinder(radius: float = 1.0, height: float = 2.0, segments: int = 16) -> str:
    lines = ["# NexusMind Generated Cylinder"]
    h2 = height / 2

    # Top and bottom circle vertices
    for z in [-h2, h2]:
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            lines.append(f"v {x:.4f} {y:.4f} {z:.4f}")

    # Center vertices for caps
    lines.append(f"v 0.0000 0.0000 {-h2:.4f}")
    lines.append(f"v 0.0000 0.0000 {h2:.4f}")

    bottom_center = 2 * segments + 1
    top_center = 2 * segments + 2

    # Side faces
    for i in range(segments):
        a = i + 1
        b = (i + 1) % segments + 1
        c = segments + (i + 1) % segments + 1
        d = segments + i + 1
        lines.append(f"f {a} {b} {c} {d}")

    # Bottom cap
    for i in range(segments):
        a = i + 1
        b = (i + 1) % segments + 1
        lines.append(f"f {bottom_center} {b} {a}")

    # Top cap
    for i in range(segments):
        a = segments + i + 1
        b = segments + (i + 1) % segments + 1
        lines.append(f"f {top_center} {a} {b}")

    return "\n".join(lines)


def _generate_plane(width: float = 2.0, height: float = 2.0, subdivisions: int = 4) -> str:
    lines = ["# NexusMind Generated Plane"]
    n = subdivisions + 1
    for i in range(n):
        for j in range(n):
            x = -width / 2 + width * j / subdivisions
            z = -height / 2 + height * i / subdivisions
            lines.append(f"v {x:.4f} 0.0000 {z:.4f}")

    for i in range(subdivisions):
        for j in range(subdivisions):
            a = i * n + j + 1
            b = a + 1
            c = a + n + 1
            d = a + n
            lines.append(f"f {a} {b} {c} {d}")

    return "\n".join(lines)


GENERATORS = {
    "cube": _generate_cube,
    "sphere": _generate_sphere,
    "cylinder": _generate_cylinder,
    "plane": _generate_plane,
}


@registry.tool(
    name="generate_3d_model",
    description="Generate basic 3D models (cube, sphere, cylinder, plane) and export as OBJ files.",
    category="3D",
    parameters=[
        ToolParam("shape", "string", "Shape: cube, sphere, cylinder, plane"),
        ToolParam("output", "string", "Output OBJ file path", required=False, default=""),
        ToolParam("params", "string", "JSON shape params: size, radius, height, segments, etc.", required=False, default="{}"),
    ],
)
def generate_3d_model(shape: str, output: str = "", params: str = "{}"):
    from config import UPLOADS_DIR
    import time

    p = json.loads(params) if isinstance(params, str) else params
    gen = GENERATORS.get(shape)
    if not gen:
        return {"error": f"Unknown shape: {shape}", "available": list(GENERATORS.keys())}

    try:
        obj_content = gen(**p)

        if not output:
            timestamp = int(time.time())
            output = str(UPLOADS_DIR / f"model_{shape}_{timestamp}.obj")

        out_path = Path(output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(obj_content)

        vertex_count = obj_content.count("\nv ")
        face_count = obj_content.count("\nf ")

        return {
            "output": str(out_path),
            "shape": shape,
            "vertices": vertex_count,
            "faces": face_count,
            "format": "OBJ",
        }
    except Exception as e:
        return {"error": str(e)}
