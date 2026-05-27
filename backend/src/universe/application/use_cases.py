"""Backward-compat re-export of universe CRUD and queries."""
from .crud import _serialize  # noqa: F401
from .crud import *  # noqa: F401,F403
from .queries import *  # noqa: F401,F403
