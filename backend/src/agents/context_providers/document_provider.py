"""DocumentContextProvider — CV, cover letter, portfolio generation.

Knowledge namespace: "documents"
Memory scope: "document_generation"
Tools: document retrieval, CV generation proposals, template selection.
"""
from __future__ import annotations

from src.agents.context_providers.base import BaseContextProvider


class DocumentContextProvider(BaseContextProvider):
    name = "document_engineer"
    knowledge_namespace = "documents"
    memory_scope = "document_generation"
