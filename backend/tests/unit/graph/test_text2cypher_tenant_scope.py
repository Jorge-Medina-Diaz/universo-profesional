"""Security tests for Text2Cypher tenant-scoping + ontology allowlist.

RLS does not cover the AGE label tables, so the generated-Cypher validator is
the entire tenant boundary for graph reads. These tests pin the fail-closed
behaviour: the server user_id is forced (never trusted from the LLM), inline
UUIDs and unscoped personal queries are rejected, and only ontology
labels/edge types may appear.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import uuid4

from src.graph.application.text2cypher import Text2CypherEngine, _validate_query
from src.graph.domain import schema

PERSONAL = schema.GRAPH_PERSONAL
ONTOLOGY = schema.GRAPH_ONTOLOGY


class TestValidateQuery:
    def test_valid_personal_query_passes(self):
        q = "MATCH (n:Skill {user_id: $user_id}) WHERE n.valid_to IS NULL RETURN n.id"
        assert _validate_query(q, graph=PERSONAL) is None

    def test_missing_user_id_binding_rejected(self):
        q = "MATCH (n:Skill) RETURN n.id"
        err = _validate_query(q, graph=PERSONAL)
        assert err is not None and "tenant scope" in err

    def test_smuggled_uuid_literal_rejected(self):
        # Properly bound to $user_id, but smuggles a victim id elsewhere — the
        # UUID-literal guard catches what the tenant-scope check would miss.
        victim = uuid4()
        q = f"MATCH (n:Skill {{user_id: $user_id}}) WHERE n.id = '{victim}' RETURN n.id"
        err = _validate_query(q, graph=PERSONAL)
        assert err is not None and "literal id" in err

    def test_literal_user_id_is_not_real_scope(self):
        # user_id bound to a literal (not $user_id) is not tenant scoping → rejected.
        victim = uuid4()
        q = f"MATCH (n:Skill {{user_id: '{victim}'}}) RETURN n.id"
        assert _validate_query(q, graph=PERSONAL) is not None

    def test_unknown_vertex_label_rejected(self):
        q = "MATCH (n:Salary {user_id: $user_id}) RETURN n"
        err = _validate_query(q, graph=PERSONAL)
        assert err is not None and "unknown vertex label" in err

    def test_unknown_edge_type_rejected(self):
        q = "MATCH (a:Skill {user_id: $user_id})-[:HACKS]->(b:Skill) RETURN b"
        err = _validate_query(q, graph=PERSONAL)
        assert err is not None and "unknown edge type" in err

    def test_write_keyword_rejected(self):
        q = "MATCH (n:Skill {user_id: $user_id}) SET n.x = 1 RETURN n"
        err = _validate_query(q, graph=PERSONAL)
        assert err is not None and "write operations" in err

    def test_age_unsupported_functions_rejected(self):
        for q in (
            "MATCH (n:Skill {user_id: $user_id}) RETURN nodes(n)",
            "MATCH p=shortestPath((a)-[*]-(b)) RETURN p",
        ):
            err = _validate_query(q, graph=PERSONAL)
            assert err is not None and "forbidden" in err

    def test_ontology_query_needs_no_user_id(self):
        q = "MATCH (o:Occupation) RETURN o.preferredLabel"
        assert _validate_query(q, graph=ONTOLOGY) is None

    def test_ontology_edge_allowed(self):
        q = "MATCH (s:EscoSkill)-[:ESSENTIAL_FOR]->(o:Occupation) RETURN o.code"
        assert _validate_query(q, graph=ONTOLOGY) is None


class TestGenerateForcesTenantId:
    async def test_llm_supplied_user_id_is_overwritten(self, monkeypatch):
        server_uid = uuid4()
        victim = str(uuid4())
        engine = Text2CypherEngine(session=MagicMock(), user_id=server_uid)

        async def fake_llm(_messages):
            return json.dumps(
                {
                    "cypher": "MATCH (n:Skill {user_id: $user_id}) RETURN n.id",
                    "params": {"user_id": victim},
                    "explanation": "list skills",
                }
            )

        monkeypatch.setattr(engine, "_call_llm", fake_llm)
        result = await engine.generate("list my skills")

        assert result.error is None
        assert result.params["user_id"] == str(server_uid)
        assert result.params["user_id"] != victim

    async def test_inline_victim_uuid_is_rejected(self, monkeypatch):
        server_uid = uuid4()
        victim = str(uuid4())
        engine = Text2CypherEngine(session=MagicMock(), user_id=server_uid)

        async def fake_llm(_messages):
            return json.dumps(
                {
                    "cypher": f"MATCH (n:Skill {{user_id: '{victim}'}}) RETURN n.id",
                    "params": {},
                    "explanation": "sneaky",
                }
            )

        monkeypatch.setattr(engine, "_call_llm", fake_llm)
        result = await engine.generate("list skills")

        # Rejected: a literal user_id is not bound to the $user_id param, so the
        # tenant-scope guard fires (the model cannot pin us to a victim's id).
        assert result.error is not None
