"""
Physics Simulation — 2D physics simulations using Pymunk.
"""
import json
import math
from typing import List, Dict, Any, Optional
from core.tool_registry import registry, ToolParam

try:
    import pymunk
    HAS_PYMUNK = True
except ImportError:
    HAS_PYMUNK = False


class PhysicsSimulator:
    """2D physics simulation engine."""

    def __init__(self):
        self.spaces: Dict[str, pymunk.Space] = {}

    def create_space(self, sim_id: str, gravity: tuple = (0, -981)) -> str:
        if not HAS_PYMUNK:
            return "pymunk not installed"
        space = pymunk.Space()
        space.gravity = gravity
        self.spaces[sim_id] = space
        return f"Space '{sim_id}' created with gravity {gravity}"

    def add_body(self, sim_id: str, body_type: str, mass: float,
                 position: tuple, shape_type: str = "circle",
                 size: float = 20, vertices: list = None, elasticity: float = 0.8,
                 friction: float = 0.5) -> Dict:
        space = self.spaces.get(sim_id)
        if not space:
            return {"error": f"Space '{sim_id}' not found"}

        bt = {
            "dynamic": pymunk.Body.DYNAMIC,
            "static": pymunk.Body.STATIC,
            "kinematic": pymunk.Body.KINEMATIC,
        }.get(body_type, pymunk.Body.DYNAMIC)

        if bt == pymunk.Body.STATIC:
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            moment = pymunk.moment_for_circle(mass, 0, size)
            body = pymunk.Body(mass, moment, body_type=bt)

        body.position = position

        if shape_type == "circle":
            shape = pymunk.Circle(body, size)
        elif shape_type == "box":
            shape = pymunk.Poly.create_box(body, (size * 2, size * 2))
        elif shape_type == "segment":
            verts = vertices or [(-size, 0), (size, 0)]
            shape = pymunk.Segment(body, verts[0], verts[1], 3)
        else:
            shape = pymunk.Circle(body, size)

        shape.elasticity = elasticity
        shape.friction = friction
        space.add(body, shape)

        return {"body_id": id(body), "position": list(position), "type": body_type}

    def step(self, sim_id: str, dt: float = 1/60, steps: int = 1) -> List[Dict]:
        space = self.spaces.get(sim_id)
        if not space:
            return [{"error": f"Space '{sim_id}' not found"}]

        for _ in range(steps):
            space.step(dt)

        results = []
        for body in space.bodies:
            results.append({
                "id": id(body),
                "position": [round(body.position.x, 2), round(body.position.y, 2)],
                "velocity": [round(body.velocity.x, 2), round(body.velocity.y, 2)],
                "angle": round(body.angle, 4),
                "angular_velocity": round(body.angular_velocity, 4),
                "type": str(body.body_type),
            })
        return results

    def run_simulation(self, sim_id: str, duration: float = 2.0,
                       dt: float = 1/60, sample_interval: float = 0.1) -> List[List[Dict]]:
        """Run a full simulation and return sampled frames."""
        frames = []
        total_steps = int(duration / dt)
        sample_every = max(1, int(sample_interval / dt))

        for i in range(total_steps):
            space = self.spaces.get(sim_id)
            if not space:
                break
            space.step(dt)
            if i % sample_every == 0:
                frame = self.step(sim_id, dt=0, steps=0)
                # Just read positions without stepping again
                frame_data = []
                for body in space.bodies:
                    frame_data.append({
                        "position": [round(body.position.x, 2), round(body.position.y, 2)],
                        "velocity": [round(body.velocity.x, 2), round(body.velocity.y, 2)],
                    })
                frames.append({"time": round(i * dt, 3), "bodies": frame_data})
        return frames

    def remove_space(self, sim_id: str):
        if sim_id in self.spaces:
            del self.spaces[sim_id]


# Global simulator
simulator = PhysicsSimulator()


@registry.tool(
    name="physics_simulate",
    description="Run a 2D physics simulation. Create spaces, add bodies, step the simulation. Supports projectiles, collisions, pendulums, etc.",
    category="Math & Physics",
    parameters=[
        ToolParam("action", "string", "Action: create_space, add_body, step, run, remove"),
        ToolParam("sim_id", "string", "Simulation ID (any string)"),
        ToolParam("params", "string", "JSON parameters for the action", required=False, default="{}"),
    ],
)
def physics_simulate(action: str, sim_id: str, params: str = "{}"):
    if not HAS_PYMUNK:
        return {"error": "pymunk not installed. Install with: pip install pymunk"}

    p = json.loads(params) if isinstance(params, str) else params

    if action == "create_space":
        gravity = tuple(p.get("gravity", (0, -981)))
        return simulator.create_space(sim_id, gravity)

    elif action == "add_body":
        return simulator.add_body(
            sim_id,
            body_type=p.get("type", "dynamic"),
            mass=p.get("mass", 1.0),
            position=tuple(p.get("position", (0, 0))),
            shape_type=p.get("shape", "circle"),
            size=p.get("size", 20),
            elasticity=p.get("elasticity", 0.8),
            friction=p.get("friction", 0.5),
        )

    elif action == "step":
        return simulator.step(sim_id, dt=p.get("dt", 1/60), steps=p.get("steps", 60))

    elif action == "run":
        return simulator.run_simulation(
            sim_id,
            duration=p.get("duration", 2.0),
            dt=p.get("dt", 1/60),
            sample_interval=p.get("sample_interval", 0.1),
        )

    elif action == "remove":
        simulator.remove_space(sim_id)
        return {"removed": sim_id}

    return {"error": f"Unknown action: {action}"}
