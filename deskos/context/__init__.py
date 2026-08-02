"""Context package: converts Events into a ContextSnapshot (user state)."""
from deskos.context.interfaces import ContextInferer
from deskos.context.context_engine import RuleBasedContextEngine

__all__ = ["ContextInferer", "RuleBasedContextEngine"]
