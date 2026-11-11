"""General utility functions for ECE backend."""

from uuid import UUID
from typing import Union, Optional, Any


def ensure_uuid(val: Any) -> Optional[UUID]:
    """Safely convert a string or UUID to a UUID instance, handling None gracefully."""
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
    return UUID(val_str)
