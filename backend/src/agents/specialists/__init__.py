"""Per-entity specialists.

Each specialist is an `Agent` focused on one universe entity (experience,
education, skill, …). Specialists share two kinds of tools:

* server-side write tools (call universe use cases directly) — never visible
  to the user, used after HITL confirmation arrives back from the frontend
* `external_execution=True` tools — generative UI cards rendered in the chat;
  the model "calls" them and Agno streams the arguments to the client as an
  AG-UI tool-call event that CopilotKit renders as a confirm/edit card
"""
