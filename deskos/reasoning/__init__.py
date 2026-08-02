"""Reasoning package: turns Context + Knowledge into candidate Suggestions.

Future AI module — initially rule-based, later replaceable with an LLM
call without changing the Reasoner interface consumers depend on.
"""
from deskos.reasoning.interfaces import Reasoner
from deskos.reasoning.rule_based_reasoner import RuleBasedReasoner

__all__ = ["Reasoner", "RuleBasedReasoner"]
