"""DocumentContextProvider — CV, cover letter, portfolio generation.

Knowledge namespace: "documents"
Memory scope: "document_generation"
Tools: document retrieval, CV generation proposals, template selection.
"""
from __future__ import annotations

from typing import Any, Callable

from src.agents.context_providers.base import BaseContextProvider
from src.agents.tools.product_reads import list_documents
from src.agents.tools.ui_widgets import (
    propose_cover_letter,
    propose_cv_regenerate,
    present_document_preview,
)


class DocumentContextProvider(BaseContextProvider):
    name = "document_engineer"
    knowledge_namespace = "documents"
    memory_scope = "document_generation"

    def get_tools(self) -> list[Callable[..., Any]]:
        return [
            list_documents,
            propose_cv_regenerate,
            propose_cover_letter,
            present_document_preview,
        ]
