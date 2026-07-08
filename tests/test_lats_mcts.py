"""Tests for the full MCTS upgrade of the LATS reasoning strategy."""
from __future__ import annotations

import math

from petfishframework import Agent
from petfishframework.core.types import ToolCall
from petfishframework.models.fake import FakeModel
from petfishframework.observability.sinks import ListSink
from petfishframework.reasoning.lats import LATS, _MCTSNode
from petfishframework.tools.calculator import Calculator


def test_mcts_node_ucb1_calculation() -> None:
    """_MCTSNode.ucb1 returns correct exploitation + exploration value."""
    parent = _MCTSNode(
        state="root",
        parent=None,
        action=None,
        exploration_constant=2.0,
    )
    parent.visits = 16

    child = _MCTSNode(
        state="child",
        parent=parent,
        action=ToolCall(id="1", name="x", arguments={}),
        exploration_constant=2.0,
    )
    child.visits = 2
    child.total_value = 6.0
    parent.children.append(child)

    expected = 3.0 + 2.0 * math.sqrt(math.log(16) / 2)
    assert abs(child.ucb1 - expected) < 1e-9


def test_mcts_select_uses_ucb() -> None:
    """With n_simulations > 1, selection uses UCB not just greedy."""
    parent = _MCTSNode(
        state="root",
        parent=None,
        action=None,
        exploration_constant=2.0,
    )
    parent.visits = 50

    high_value_child = _MCTSNode(
        state="high",
        parent=parent,
        action=ToolCall(id="1", name="high", arguments={}),
        exploration_constant=2.0,
    )
    high_value_child.visits = 20
    high_value_child.total_value = 20.0  # average 1.0

    low_value_child = _MCTSNode(
        state="low",
        parent=parent,
        action=ToolCall(id="2", name="low", arguments={}),
        exploration_constant=2.0,
    )
    low_value_child.visits = 1
    low_value_child.total_value = 0.0  # average 0.0

    parent.children = [high_value_child, low_value_child]

    selected = LATS()._select_best_child(parent)
    assert selected is low_value_child


def test_backprop_updates_visits_and_value() -> None:
    """After simulation, parent visits and total_value updated."""
    root = _MCTSNode(state="root", parent=None, action=None)
    root.visits = 5
    root.total_value = 10.0

    child = _MCTSNode(
        state="child",
        parent=root,
        action=ToolCall(id="1", name="child_action", arguments={}),
    )
    child.visits = 2
    child.total_value = 4.0
    root.children.append(child)

    grandchild = _MCTSNode(
        state="grandchild",
        parent=child,
        action=ToolCall(id="2", name="grandchild_action", arguments={}),
    )
    child.children.append(grandchild)

    LATS()._backpropagate(grandchild, 7.0)

    assert grandchild.visits == 1
    assert grandchild.total_value == 7.0
    assert child.visits == 3
    assert child.total_value == 11.0
    assert root.visits == 6
    assert root.total_value == 17.0


def test_n_simulations_controls_iterations() -> None:
    """n_simulations=4 runs 4 MCTS iterations before selecting action."""
    sink = ListSink()
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(n_simulations=4, breadth=3, max_depth=1),
        tools=(Calculator(),),
    )

    session = agent.session("Calculate (2 + 3) * 4")
    session.events.subscribe(sink)
    session.run()

    simulation_events = [e for e in sink.events if e.type == "lats.simulation"]
    assert len(simulation_events) == 4


def test_backward_compat_n_simulations_1() -> None:
    """n_simulations=1 behaves like the old simplified greedy selection."""
    model = FakeModel.lats_scenario()
    agent = Agent(
        model=model,
        reasoning=LATS(n_simulations=1, breadth=3, max_depth=5),
        tools=(Calculator(),),
    )

    result = agent.run("Calculate (2 + 3) * 4")

    assert "20" in result.answer
    assert len(result.trajectory.steps) >= 2
    tool_steps = [s for s in result.trajectory.steps if s.tool_name == "calculator"]
    assert len(tool_steps) >= 2
    assert tool_steps[0].tool_args == {"expression": "2+3"}
    assert tool_steps[0].observation == "5"
    assert tool_steps[1].tool_args == {"expression": "5*4"}
    assert tool_steps[1].observation == "20"
