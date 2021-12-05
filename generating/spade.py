from __future__ import annotations

from typing import TYPE_CHECKING, List

from intermediate.action import (Add, AddElement, Block, Declaration, Divide,
                                 IfEqual, IfGreaterThan, IfGreaterThanOrEqual,
                                 IfLessThan, IfLessThanOrEqual, IfNotEqual,
                                 Multiply, Set, Subtract, WhileEqual,
                                 WhileGreaterThan, WhileGreaterThanOrEqual,
                                 WhileLessThan, WhileLessThanOrEqual,
                                 WhileNotEqual)

if TYPE_CHECKING:
    from intermediate.agent import Agent
    from intermediate.behaviour import Behaviour
    from parsing.argument import Argument
    from parsing.state import ParsedData
    

class SpadeCode:
    INDENT_SIZE = 4
    
    def __init__(self, parsed_data: ParsedData):
        self.indent: int = 0
        self.code_lines: List[str] = []
        self.add_required_imports()
        if parsed_data.messages:
            self.add_newlines(2)
            self.add_base_message()
        for agent in parsed_data.agents:
            self.add_newlines(2)
            self.generate_agent(agent)
    
    ### COMMON ###
    def add_required_imports(self) -> List[str]:
        self.add_line('import json')
        self.add_line('import random')
        self.add_line('import numpy')
        self.add_line('import spade')
        
    def indent_left(self) -> None:
        self.indent -= 1
        
    def indent_right(self) -> None:
        self.indent += 1
        
    def add_line(self, line: str) -> None:
        self.code_lines.append(SpadeCode.INDENT_SIZE * self.indent * ' ' + line + '\n')
        
    def add_newline(self) -> None:
        self.add_line('')
        
    def add_newlines(self, count: int) -> None:
        for _ in range(count):
            self.add_newline()
            
    ### BASE MESSAGE ###
    def add_base_message(self) -> None:
        self.add_line('class BaseMessage:')
        self.indent_right()
        self.add_line('def __init__(self, _type, performative):')
        self.indent_right()
        self.add_line('self.type = _type')
        self.add_line('self.performative = performative')
        self.add_line('self.body = {}')
        self.indent_left()
        self.add_newline()
        self.add_line('def get_spade_message(self):')
        self.indent_right()
        self.add_line('msg = spade.message.Message()')
        self.add_line('msg.metadata["type"] = self.body["type"] = self.type')
        self.add_line('msg.metadata["performative"] = self.body["performative"] = self.performative')
        self.add_line('msg.body = json.dumps(self.body)')
        self.add_line('return msg')
        self.indent_left()
        self.indent_left()
    
    ### AGENT ###
    def generate_agent(self, agent: Agent) -> None:
        self.add_line(f'class {agent.name}(spade.agent.Agent):')
        self.indent_right()
        self.add_agent_constructor(agent)
        self.add_newline()
        self.add_agent_setup(agent)
        self.add_newline()
        for setup_behaviour in agent.setup_behaviours.values():
            self.add_agent_behaviour(setup_behaviour, 'spade.behaviour.OneShotBehaviour')
        self.indent_left()
        
    def add_agent_constructor(self, agent: Agent) -> None:
        self.add_line('def __init__(self, jid, password, location, connections):')
        self.indent_right()
        self.add_line('super().__init__(jid, password, verify_security=False)')
        self.add_line('self.location = location')
        self.add_line('self.connections = connections')
        for init_float_param in agent.init_floats.values():
            self.add_line(f'self.{init_float_param.name} = {init_float_param.value}')
        for dist_normal_float_param in agent.dist_normal_floats.values():
            self.add_line(f'self.{dist_normal_float_param.name} = numpy.random.normal({dist_normal_float_param.mean}, {dist_normal_float_param.std_dev})')
        for enum_param in agent.enums.values():            
            names = []
            weights = []
            for name, weight in enum_param.enums:
                names.append(f'\"{name}\"')
                weights.append(weight)
            names = f'[{", ".join(names)}]'
            weights = f'[{", ".join(weights)}]'
            self.add_line(f'self.{enum_param.name} = random.choices({names}, {weights})[0]')
        for list_param in agent.lists.values():
            self.add_line(f'self.{list_param.name} = []')
        self.indent_left()
        
    def add_agent_setup(self, agent: Agent) -> None:
        self.add_line('def setup(self):')
        self.indent_right()
        if not agent.setup_behaviours.values():
            self.add_line('...')
        for setup_behaviour in agent.setup_behaviours.values():
            self.add_line(f'self.add_behaviour(self.{setup_behaviour.name}())')
        self.indent_left()
            
    def add_agent_behaviour(self, behaviour: Behaviour, behaviour_type: str) -> None:
        self.add_line(f'class {behaviour.name}({behaviour_type}):')
        self.indent_right()
        if not behaviour.actions.values():
            self.add_line('...')
        for action in behaviour.actions.values():
            self.add_line(f'async def {action.name}(self):')
            self.indent_right()
            self.add_block(action.main_block)
            self.indent_left()
            self.add_newline()
        self.add_line('async def run(self):')
        self.indent_right()
        if not behaviour.actions.values():
            self.add_line('...')
        for action in behaviour.actions.values():
            self.add_line(f'await self.{action.name}()')
        self.indent_left()
        self.indent_left()
        
    def agent_param(self, arg: Argument) -> str:
        return 'self.agent.' if arg.is_agent_param else ''
    
    def parse_instruction_arg(self, arg: Argument) -> str:
        if arg.is_agent_param:
            return 'self.agent.' + arg.expr
        # num value
        elif arg.is_enum:
            return f'\"{arg.expr}\"'
        # float
        else:
            return arg.expr
        
    def add_block(self, block: Block) -> None:
        if not block.statements:
            self.add_line('...')
            
        for statement in block.statements:
            if isinstance(statement, Block):
                self.indent_right()
                self.add_block(statement)
                self.indent_left()
                
            elif isinstance(statement, Declaration):
                self.add_line(f'{statement.name} = {self.agent_param(statement.value)}{statement.value.expr}')
                
            elif isinstance(statement, AddElement):
                self.add_line(f'self.agent.{statement.arg1.expr}.append({statement.arg2.expr})')
                
            else:
                arg1 = self.parse_instruction_arg(statement.arg1)
                arg2 = self.parse_instruction_arg(statement.arg2)
                if isinstance(statement, IfGreaterThan):
                    self.add_line(f'if {arg1} > {arg2}:')
                elif isinstance(statement, IfGreaterThanOrEqual):
                    self.add_line(f'if {arg1} >= {arg2}:')
                elif isinstance(statement, IfLessThan):
                    self.add_line(f'if {arg1} < {arg2}:')
                elif isinstance(statement, IfLessThanOrEqual):
                    self.add_line(f'if {arg1} <= {arg2}:')
                elif isinstance(statement, IfEqual):
                    self.add_line(f'if {arg1} == {arg2}:')
                elif isinstance(statement, IfNotEqual):
                    self.add_line(f'if {arg1} != {arg2}:')
                elif isinstance(statement, WhileGreaterThan):
                    self.add_line(f'while {arg1} > {arg2}:')
                elif isinstance(statement, WhileGreaterThanOrEqual):
                    self.add_line(f'while {arg1} >= {arg2}:')
                elif isinstance(statement, WhileLessThan):
                    self.add_line(f'while {arg1} < {arg2}:')
                elif isinstance(statement, WhileLessThanOrEqual):
                    self.add_line(f'while {arg1} <= {arg2}:')
                elif isinstance(statement, WhileEqual):
                    self.add_line(f'while {arg1} == {arg2}:')
                elif isinstance(statement, WhileNotEqual):
                    self.add_line(f'while {arg1} != {arg2}:')
                elif isinstance(statement, Add):
                    self.add_line(f'{arg1} += {arg2}')
                elif isinstance(statement, Subtract):
                    self.add_line(f'{arg1} -= {arg2}')
                elif isinstance(statement, Multiply):
                    self.add_line(f'{arg1} *= {arg2}')
                elif isinstance(statement, Divide):
                    self.add_line(f'{arg1} /= {arg2}')
                elif isinstance(statement, Set):
                    self.add_line(f'{arg1} = {arg2}')
