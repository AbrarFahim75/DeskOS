"""Services package: integrations that execute approved Actions.

Services never invent actions — they only execute what the Decision Engine
approved. Each Service handles the subset of ActionTypes it knows about and
ignores the rest.
"""
from deskos.services.interfaces import Service
from deskos.services.timer_service import TimerService
from deskos.services.notification_service import NotificationService
from deskos.services.service_registry import ServiceRegistry

__all__ = ["Service", "TimerService", "NotificationService", "ServiceRegistry"]
