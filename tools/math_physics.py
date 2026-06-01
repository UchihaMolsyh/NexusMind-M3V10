"""
Math & Physics Engine — symbolic math solving and physics computations.
"""
import json
import sympy as sp
import numpy as np
from core.tool_registry import registry, ToolParam


# ─── Math Solver ──────────────────────────────────────────────

@registry.tool(
    name="math_solve",
    description="Solve mathematical equations, simplify expressions, compute integrals/derivatives, linear algebra, and more. Supports symbolic and numeric math.",
    category="Math & Physics",
    parameters=[
        ToolParam("expression", "string", "Math expression or equation to solve (e.g., 'x**2 + 3*x - 4 = 0', 'integrate(sin(x), x)', 'diff(x**3, x)')"),
        ToolParam("operation", "string", "Operation type: solve, simplify, integrate, differentiate, limit, series, factor, expand, matrix, evaluate", required=False, default="solve"),
        ToolParam("variable", "string", "Variable to solve for (default: x)", required=False, default="x"),
    ],
)
def math_solve(expression: str, operation: str = "solve", variable: str = "x"):
    x, y, z, t, a, b, c, n = sp.symbols("x y z t a b c n")
    local_vars = {"x": x, "y": y, "z": z, "t": t, "a": a, "b": b, "c": c, "n": n,
                  "pi": sp.pi, "e": sp.E, "I": sp.I, "oo": sp.oo,
                  "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
                  "log": sp.log, "ln": sp.ln, "exp": sp.exp,
                  "sqrt": sp.sqrt, "Abs": sp.Abs,
                  "integrate": sp.integrate, "diff": sp.diff,
                  "limit": sp.limit, "series": sp.series,
                  "Matrix": sp.Matrix, "Rational": sp.Rational}

    var = local_vars.get(variable, sp.Symbol(variable))

    try:
        if operation == "solve":
            if "=" in expression and "==" not in expression:
                lhs, rhs = expression.split("=", 1)
                expr = sp.sympify(lhs.strip(), locals=local_vars) - sp.sympify(rhs.strip(), locals=local_vars)
            else:
                expr = sp.sympify(expression, locals=local_vars)
            result = sp.solve(expr, var)
            return {"operation": "solve", "input": expression, "solutions": [str(r) for r in result], "latex": [sp.latex(r) for r in result]}

        elif operation == "simplify":
            expr = sp.sympify(expression, locals=local_vars)
            simplified = sp.simplify(expr)
            return {"operation": "simplify", "input": expression, "result": str(simplified), "latex": sp.latex(simplified)}

        elif operation == "integrate":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.integrate(expr, var)
            return {"operation": "integrate", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "differentiate":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.diff(expr, var)
            return {"operation": "differentiate", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "limit":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.limit(expr, var, 0)
            return {"operation": "limit", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "series":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.series(expr, var, 0, 6)
            return {"operation": "series", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "factor":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.factor(expr)
            return {"operation": "factor", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "expand":
            expr = sp.sympify(expression, locals=local_vars)
            result = sp.expand(expr)
            return {"operation": "expand", "input": expression, "result": str(result), "latex": sp.latex(result)}

        elif operation == "matrix":
            expr = sp.sympify(expression, locals=local_vars)
            if isinstance(expr, sp.Matrix):
                det = expr.det() if expr.is_square else "N/A"
                return {"operation": "matrix", "matrix": str(expr), "determinant": str(det), "shape": list(expr.shape)}
            return {"error": "Expression is not a matrix"}

        elif operation == "evaluate":
            expr = sp.sympify(expression, locals=local_vars)
            result = float(expr.evalf())
            return {"operation": "evaluate", "input": expression, "result": result}

        else:
            expr = sp.sympify(expression, locals=local_vars)
            return {"operation": "auto", "result": str(expr), "latex": sp.latex(expr)}

    except Exception as e:
        return {"error": str(e), "input": expression, "operation": operation}


# ─── Physics Solver ───────────────────────────────────────────

@registry.tool(
    name="physics_solve",
    description="Solve physics problems: kinematics, dynamics, energy, waves, electricity, thermodynamics, optics.",
    category="Math & Physics",
    parameters=[
        ToolParam("problem_type", "string", "Type: kinematics, dynamics, energy, wave, electric, thermo, optics"),
        ToolParam("known_values", "string", "JSON dict of known values, e.g. '{\"v0\": 10, \"a\": 9.8, \"t\": 2}'"),
        ToolParam("solve_for", "string", "Variable to solve for"),
    ],
)
def physics_solve(problem_type: str, known_values: str, solve_for: str):
    vals = json.loads(known_values) if isinstance(known_values, str) else known_values

    # Define common physics symbols
    syms = {name: sp.Symbol(name) for name in
            ["v0", "v", "a", "t", "x", "x0", "m", "F", "g", "h",
             "KE", "PE", "W", "P", "f", "T", "lam", "omega", "k",
             "q", "V", "I", "R", "C", "L", "E", "B",
             "Q", "Tc", "Th", "eta", "n", "theta"]}

    g_val = 9.80665  # standard gravity

    # Physics equations by category
    equations = {
        "kinematics": [
            sp.Eq(syms["v"], syms["v0"] + syms["a"] * syms["t"]),
            sp.Eq(syms["x"], syms["x0"] + syms["v0"] * syms["t"] + sp.Rational(1, 2) * syms["a"] * syms["t"]**2),
            sp.Eq(syms["v"]**2, syms["v0"]**2 + 2 * syms["a"] * (syms["x"] - syms["x0"])),
        ],
        "dynamics": [
            sp.Eq(syms["F"], syms["m"] * syms["a"]),
            sp.Eq(syms["W"], syms["F"] * syms["x"]),
            sp.Eq(syms["P"], syms["F"] * syms["v"]),
        ],
        "energy": [
            sp.Eq(syms["KE"], sp.Rational(1, 2) * syms["m"] * syms["v"]**2),
            sp.Eq(syms["PE"], syms["m"] * syms["g"] * syms["h"]),
            sp.Eq(syms["W"], syms["KE"] - sp.Rational(1, 2) * syms["m"] * syms["v0"]**2),
        ],
        "wave": [
            sp.Eq(syms["v"], syms["f"] * syms["lam"]),
            sp.Eq(syms["T"], 1 / syms["f"]),
            sp.Eq(syms["omega"], 2 * sp.pi * syms["f"]),
        ],
        "electric": [
            sp.Eq(syms["V"], syms["I"] * syms["R"]),
            sp.Eq(syms["P"], syms["I"] * syms["V"]),
            sp.Eq(syms["P"], syms["I"]**2 * syms["R"]),
        ],
        "thermo": [
            sp.Eq(syms["eta"], 1 - syms["Tc"] / syms["Th"]),
            sp.Eq(syms["Q"], syms["m"] * syms["C"] * (syms["Th"] - syms["Tc"])),
        ],
        "optics": [
            sp.Eq(1 / syms["f"], 1 / syms["x0"] + 1 / syms["x"]),
            sp.Eq(syms["n"] * sp.sin(syms["theta"]), syms["n"] * sp.sin(syms["theta"])),
        ],
    }

    eqs = equations.get(problem_type, [])
    if not eqs:
        return {"error": f"Unknown problem type: {problem_type}", "available": list(equations.keys())}

    target = syms.get(solve_for)
    if not target:
        return {"error": f"Unknown variable: {solve_for}"}

    # Substitute known values
    solutions = []
    for eq in eqs:
        if target in eq.free_symbols:
            substituted = eq
            for name, value in vals.items():
                if name in syms:
                    substituted = substituted.subs(syms[name], value)
            try:
                sol = sp.solve(substituted, target)
                if sol:
                    solutions.extend(sol)
            except Exception:
                continue

    if solutions:
        return {
            "problem_type": problem_type,
            "solve_for": solve_for,
            "solutions": [str(s) for s in solutions],
            "numeric": [float(s.evalf()) if s.is_number else str(s) for s in solutions],
            "known_values": vals,
        }
    return {"error": "Could not solve with given values", "known": vals, "solve_for": solve_for}
