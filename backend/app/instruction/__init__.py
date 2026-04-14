"""
指令执行模块

支持文档智能操作交互，包括意图解析和指令执行
"""
from .intent_parser import IntentParser, intent_parser
from .executor import InstructionExecutor, instruction_executor

__all__ = [
    "IntentParser",
    "intent_parser",
    "InstructionExecutor",
    "instruction_executor",
]
