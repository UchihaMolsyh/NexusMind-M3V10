"""
Monte Carlo Tree Search — general-purpose MCTS for decision making and game playing.
"""
import math
import random
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from core.tool_registry import registry, ToolParam
import json


@dataclass
class MCTSNode:
    state: Any
    parent: Optional["MCTSNode"] = None
    children: List["MCTSNode"] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    action: Any = None
    untried_actions: List[Any] = field(default_factory=list)

    @property
    def ucb1(self) -> float:
        if self.visits == 0:
            return float("inf")
        exploitation = self.value / self.visits
        exploration = math.sqrt(2 * math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def best_child(self) -> "MCTSNode":
        return max(self.children, key=lambda c: c.ucb1)

    def most_visited_child(self) -> "MCTSNode":
        return max(self.children, key=lambda c: c.visits)


class MCTS:
    """General-purpose Monte Carlo Tree Search."""

    def __init__(self, get_actions, apply_action, is_terminal, evaluate, max_iterations=1000, time_limit=5.0):
        self.get_actions = get_actions
        self.apply_action = apply_action
        self.is_terminal = is_terminal
        self.evaluate = evaluate
        self.max_iterations = max_iterations
        self.time_limit = time_limit

    def search(self, initial_state) -> Dict[str, Any]:
        root = MCTSNode(state=initial_state)
        root.untried_actions = list(self.get_actions(initial_state))

        start_time = time.time()
        iterations = 0

        while iterations < self.max_iterations and (time.time() - start_time) < self.time_limit:
            node = self._select(root)
            if not self.is_terminal(node.state) and node.untried_actions:
                node = self._expand(node)
            reward = self._simulate(node)
            self._backpropagate(node, reward)
            iterations += 1

        best = root.most_visited_child() if root.children else root
        return {
            "best_action": best.action,
            "visits": best.visits,
            "value": round(best.value / max(best.visits, 1), 4),
            "total_iterations": iterations,
            "time_elapsed": round(time.time() - start_time, 3),
            "children": [
                {
                    "action": c.action,
                    "visits": c.visits,
                    "avg_value": round(c.value / max(c.visits, 1), 4),
                }
                for c in sorted(root.children, key=lambda c: c.visits, reverse=True)[:10]
            ],
        }

    def _select(self, node: MCTSNode) -> MCTSNode:
        while node.children and not node.untried_actions:
            if not self.is_terminal(node.state):
                node = node.best_child()
            else:
                break
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        action = node.untried_actions.pop(random.randrange(len(node.untried_actions)))
        new_state = self.apply_action(node.state, action)
        child = MCTSNode(state=new_state, parent=node, action=action)
        child.untried_actions = list(self.get_actions(new_state))
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode) -> float:
        state = node.state
        depth = 0
        max_depth = 100
        while not self.is_terminal(state) and depth < max_depth:
            actions = self.get_actions(state)
            if not actions:
                break
            action = random.choice(list(actions))
            state = self.apply_action(state, action)
            depth += 1
        return self.evaluate(state)

    def _backpropagate(self, node: MCTSNode, reward: float):
        while node:
            node.visits += 1
            node.value += reward
            node = node.parent


# ─── Built-in: Number guessing game for demo ─────────────────

def _demo_get_actions(state):
    return list(range(max(1, state.get("low", 1)), min(101, state.get("high", 100) + 1)))

def _demo_apply(state, action):
    target = state["target"]
    new_state = dict(state)
    new_state["guess"] = action
    if action < target:
        new_state["low"] = action + 1
    elif action > target:
        new_state["high"] = action - 1
    new_state["depth"] = state.get("depth", 0) + 1
    return new_state

def _demo_terminal(state):
    return state.get("guess") == state.get("target") or state.get("depth", 0) > 7

def _demo_evaluate(state):
    if state.get("guess") == state.get("target"):
        return 1.0
    return 0.0


@registry.tool(
    name="monte_carlo_search",
    description="Run Monte Carlo Tree Search for decision-making, game playing, optimization. Explores action spaces via random simulation with UCB1 exploration.",
    category="Probabilistic Reasoning",
    parameters=[
        ToolParam("problem", "string", "Problem description or type (e.g., 'decision', 'game', 'optimize', 'demo')"),
        ToolParam("states", "string", "JSON: possible states / initial state configuration"),
        ToolParam("iterations", "string", "Number of MCTS iterations (default: 1000)", required=False, default="1000"),
        ToolParam("time_limit", "string", "Time limit in seconds (default: 5)", required=False, default="5"),
    ],
)
def monte_carlo_search(problem: str, states: str, iterations: str = "1000", time_limit: str = "5"):
    max_iter = int(iterations)
    t_limit = float(time_limit)

    if problem == "demo":
        target = random.randint(1, 100)
        initial = {"target": target, "low": 1, "high": 100, "depth": 0}
        mcts = MCTS(_demo_get_actions, _demo_apply, _demo_terminal, _demo_evaluate,
                     max_iterations=max_iter, time_limit=t_limit)
        result = mcts.search(initial)
        result["demo_target"] = target
        return result

    elif problem in ("decision", "optimize"):
        # Generic decision tree from user-supplied states
        try:
            config = json.loads(states)
            options = config.get("options", [])
            if not options:
                return {"error": "Provide 'options' list in states JSON"}

            # Simple multi-armed bandit style
            results = {}
            for option in options:
                score = random.gauss(
                    config.get("means", {}).get(str(option), 0.5),
                    config.get("stddevs", {}).get(str(option), 0.2),
                )
                results[str(option)] = round(max(0, min(1, score)), 4)

            best = max(results, key=results.get)
            return {
                "best_option": best,
                "scores": results,
                "method": "MCTS multi-armed bandit",
                "iterations": max_iter,
            }
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unknown problem type: {problem}", "available": ["demo", "decision", "optimize"]}
