from __future__ import annotations

from itertools import compress
from typing import TYPE_CHECKING, List

from aasm.generating.python_code import PythonCode
from aasm.intermediate.graph import (
    AgentConstantAmount,
    AgentPercentAmount,
    ConnectionConstantAmount,
    ConnectionDistExpAmount,
    ConnectionDistNormalAmount,
    ConnectionDistUniformAmount,
    MatrixGraph,
    StatisticalGraph,
)

if TYPE_CHECKING:
    from aasm.intermediate.graph import Graph


class PythonGraph(PythonCode):
    def __init__(self, indent_size: int, graph: Graph | None):
        super().__init__(indent_size)
        if graph:
            self.add_required_imports()
            self.add_newlines(2)
            self.generate_graph(graph)

    def add_required_imports(self) -> None:
        self.add_line("import random")
        self.add_line("import uuid")
        self.add_line("import numpy")

    def generate_graph(self, graph: Graph) -> None:
        match graph:
            case StatisticalGraph():
                self.add_statistical_graph(graph)

            case MatrixGraph():
                self.add_matrix_graph(graph)

            case _:
                raise Exception(f"Unknown graph type: {graph.print()}")

    def add_statistical_graph(self, graph: StatisticalGraph) -> None:
        self.add_line("def generate_graph_structure(domain):")
        self.indent_right()

        if not graph.agents:
            self.add_line("return []")
            self.indent_left()
            return

        num_agents_expr: List[str] = []
        for agent in graph.agents.values():
            match agent.amount:
                case AgentConstantAmount():
                    self.add_line(f"_num_{agent.name} = {agent.amount.value}")

                case AgentPercentAmount():
                    self.add_line(
                        f"_num_{agent.name} = round({agent.amount.value} / 100 * {graph.size})"
                    )

                case _:
                    raise Exception(
                        f"Unknown agent amount type: {agent.amount.print()}"
                    )

            num_agents_expr.append(f"_num_{agent.name}")

        self.add_line(f'num_agents = {" + ".join(num_agents_expr)}')
        self.add_line("random_id = str(uuid.uuid4())[:5]")
        self.add_line('jids = [f"{i}_{random_id}@{domain}" for i in range(num_agents)]')
        self.add_line("agents = []")
        self.add_line("next_agent_idx = 0")
        for agent in graph.agents.values():
            self.add_line(f"for _ in range(_num_{agent.name}):")
            self.indent_right()

            match agent.connections:
                case ConnectionConstantAmount():
                    self.add_line(f"num_connections = {agent.connections.value}")

                case ConnectionDistNormalAmount():
                    self.add_line(
                        f"num_connections = int(numpy.random.normal({agent.connections.mean}, {agent.connections.std_dev}))"
                    )

                case ConnectionDistExpAmount():
                    self.add_line(
                        f"num_connections = int(numpy.random.exponential(1 / {agent.connections.lambda_}))"
                    )

                case ConnectionDistUniformAmount():
                    self.add_line(
                        f"num_connections = int(random.uniform({agent.connections.a}, {agent.connections.b}))"
                    )

                case _:
                    raise Exception(
                        f"Unknown connection amount: {agent.connections.print()}"
                    )

            self.add_line(
                "num_connections = max(min(num_connections, len(jids) - 1), 0)"
            )
            self.add_line("jid = jids[next_agent_idx]")
            self.add_line("agents.append({")
            self.indent_right()
            self.add_line('"jid": jid,')
            self.add_line(f'"type": "{agent.name}",')
            self.add_line(
                '"connections": random.sample([other_jid for other_jid in jids if other_jid != jid], num_connections),'
            )
            self.indent_left()
            self.add_line("})")
            self.add_line("next_agent_idx += 1")
            self.indent_left()

        self.add_line("return agents")
        self.indent_left()

    def add_matrix_graph(self, graph: MatrixGraph):
        self.add_line("def generate_graph_structure(domain):")
        self.indent_right()
        if not graph.agents:
            self.add_line("return []")
            self.indent_left()
            return
        if graph.is_scale_defined():
            self.add_line(f"scale_factor = {graph.scale}")
        else:
            self.add_line(f"scale_factor = 1")
        self.add_line(f"n_agent_types = {len(graph.agents)}")
        self.add_line("graph_size = scale_factor * n_agent_types")
        self.add_line("random_id = str(uuid.uuid4())[:5]")
        self.add_line('jids = [f"{i}_{random_id}@{domain}" for i in range(graph_size)]')
        self.add_line("agents = []")
        self.add_line("indx_sets = []")
        for agent in graph.agents:
            adj_indx = [True if x == 1 else False for x in agent.adj_row.row]
            adj_indx = list(compress(range(len(adj_indx)), adj_indx))
            self.add_line(f"indx_sets.append({adj_indx})")

        self.add_line("for base_agent_index in range(n_agent_types):")
        self.indent_right()
        self.add_line("indices = indx_sets[base_agent_index]")
        self.add_line("for shift in range(1, scale_factor):")
        self.indent_right()
        self.add_line(
            f"indices.append((base_agent_index + shift * n_agent_types) % graph_size)"
        )
        self.indent_left()
        self.add_line("for shift in range(scale_factor):")
        self.indent_right()
        self.add_line("jid = jids[base_agent_index + shift * n_agent_types]")
        self.add_line("connections = []")
        self.add_line("for i in indices:")
        self.indent_right()
        self.add_line(
            f"connections.append(jids[(i + shift * n_agent_types) % graph_size])"
        )
        self.indent_left()
        self.add_line("agents.append({")
        self.indent_right()
        self.add_line('"jid": jid,')
        self.add_line(f'"type": "{agent.name}",')
        self.add_line('"connections": connections,')
        self.indent_left()
        self.add_line("})")
        self.indent_left()

        self.indent_left()
        self.add_line("return agents")
        self.indent_left()
