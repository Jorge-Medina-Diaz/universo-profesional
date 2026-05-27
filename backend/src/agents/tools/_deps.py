from functools import wraps
from uuid import UUID

from agno.run.base import RunContext


def require_user_id(func):
    @wraps(func)
    async def wrapper(run_context: RunContext, *args, **kwargs):
        user_id = run_context.user_id
        if not user_id:
            return {"ok": False, "error": "missing user_id"}
        return await func(run_context, *args, **kwargs)

    # Agno's @tool stores the original callable in .entrypoint.
    # If we don't wrap it too, tests that call .entrypoint bypass the guard.
    if hasattr(func, "entrypoint"):
        original_entrypoint = func.entrypoint

        @wraps(original_entrypoint)
        async def entrypoint_wrapper(*args, **kwargs):
            if args and isinstance(args[0], RunContext):
                user_id = args[0].user_id
                if not user_id:
                    return {"ok": False, "error": "missing user_id"}
            return await original_entrypoint(*args, **kwargs)

        wrapper.entrypoint = entrypoint_wrapper

    return wrapper
