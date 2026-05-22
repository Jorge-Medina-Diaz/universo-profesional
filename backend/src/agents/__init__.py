"""Agno-based agentic chat layer.

The `agents` bounded context wires a multi-agent team (coordinator + per-entity
specialists) to a streaming AG-UI HTTP endpoint that the CopilotKit frontend
consumes. Tools delegate to the existing universe use cases — agents are an
orchestration layer, not a data layer.
"""
