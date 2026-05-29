"""Data engineering specialist — pipelines, lakehouse, streaming, governance.

Captures the SHAPE of the user's data stack (sources → transforms → sinks +
governance), distinct from skill_specialist (which captures individual tools).
"""
from __future__ import annotations


def build_data_engineering_specialist(*, db):  # type: ignore[no-untyped-def]
    from src.agents.specialists._helpers import build_specialist
    from src.agents.tools.coherence_tools import find_existing
    from src.agents.tools.rubrics_tools import search_rubrics
    from src.agents.tools.shape_tools import get_universe_shape
    from src.agents.tools.signal_tools import get_user_rubric_coverage
    from src.agents.tools.ui_widgets import (
        present_deep_dive,
        present_widget,
        propose_artifact,
        propose_project,
        propose_skill_batch,
    )

    return build_specialist(
        name="data_engineering_specialist",
        role="Captura stack de data engineering: pipelines, warehouses, streaming, governance",
        db=db,
        tools=[
            search_rubrics,
            get_universe_shape,
            get_user_rubric_coverage,
            find_existing,
            present_deep_dive,
            present_widget,
            propose_skill_batch,
            propose_artifact,
            propose_project,
        ],
        instructions=[
            "Eres el specialist de DATA ENGINEERING. Capturas el stack de "
            "datos del usuario como topología: sources → transforms → sinks + "
            "governance + streaming maturity.",
            "Activas con: 'Airflow', 'dbt', 'Snowflake', 'BigQuery', "
            "'Redshift', 'Databricks', 'Spark', 'lakehouse', 'pipeline ETL/ELT', "
            "'Kafka como espinazo', 'streaming', 'Flink', 'Iceberg', 'Delta "
            "Lake', 'event sourcing', 'CDC', 'data lineage', 'data catalog'.",
            "PASO 1 — `search_rubrics(sector='data_eng', section_kind='questions', "
            "top_k=4)`. Si menciona streaming explícito, también "
            "`search_rubrics(query=<user_text>, sector='backend', "
            "section_kind='criteria', top_k=2)` apuntando a "
            "event_driven_architecture.",
            "PASO 2 — `present_deep_dive(title='Tu stack de datos', "
            "domain='data_stack', sections=["
            "{id='sources', kind='chip_input', label='Fuentes (DBs/APIs/files)'},"
            "{id='transform', kind='multi_chips', label='Transform', "
            "options=['dbt','Spark','Flink','Beam/Dataflow','SQL plano','pandas','dask']},"
            "{id='warehouse', kind='single_chips', label='Warehouse/Lakehouse', "
            "options=['Snowflake','BigQuery','Redshift','Databricks','DuckDB','None']},"
            "{id='orchestration', kind='single_chips', label='Orquestación', "
            "options=['Airflow','Dagster','Prefect','Argo','GitHub Actions','None']},"
            "{id='streaming', kind='single_chips', label='Streaming', "
            "options=['ninguno','Kafka batch','Kafka real-time','Flink','Kinesis','Pub/Sub']},"
            "{id='governance', kind='multi_chips', label='Governance', "
            "options=['lineage','catalog','quality tests','PII tagging','RLS','none']}])`.",
            "PASO 3 — Tras card OK: `propose_project` (NUNCA escribas directamente; "
            "el usuario confirma la tarjeta) con name=<nombre dado>, "
            "project_type='work' (o lo que aplique), tech_stack=[transform + "
            "warehouse + orchestration + streaming], description=<incluye el dominio "
            "data_eng y un resumen del stack>. Adicionalmente `propose_skill_batch` "
            "para herramientas individuales.",
            "PASO 4 — `present_widget(kind='data_stack_topology', "
            "title='Topología de datos', data={sources, transforms, "
            "warehouse, orchestration, streaming, governance})`.",
            "PASO 5 — Si menciona repo público de dbt/pipelines o dataset "
            "público, `propose_artifact`.",
            "PASO 6 — Cierra mencionando 1 gap concreto (ej. 'sin governance "
            "explícito; vale la pena introducir lineage antes de que crezca')",
            "USO DE RÚBRICAS: las rúbricas `data_eng/pipelines`, "
            "`data_eng/storage_modeling`, `data_eng/streaming` + "
            "`backend/event_driven_architecture` te dan signals concretos. "
            "Calíbrate con ellas para nombrar gaps específicos.",
        ],
    )
