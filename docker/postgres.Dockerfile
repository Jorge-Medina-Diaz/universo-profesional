# Postgres 16 with pgvector + Apache AGE compiled in.
#
# We need both:
#   - pgvector: dense embeddings (existing HNSW indexes)
#   - Apache AGE: openCypher over relational, used for the graph universe.
#
# Trade-off: there is no reliable pre-built image for PG16 that bundles both
# pgvector and Apache AGE. Community images (e.g. sohamthakurdesai/postgres-age-pgvector)
# target PG15, and apache/age is a standalone server rather than an extension
# layer on top of pgvector. Building AGE from source adds ~3 min on a cold
# build, but Docker layer caching eliminates that cost afterwards.
ARG AGE_REF=PG16/v1.5.0-rc0

FROM pgvector/pgvector:pg16 AS age-builder

ARG AGE_REF

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        bison \
        flex \
        git \
        libreadline-dev \
        postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth 1 --branch "${AGE_REF}" https://github.com/apache/age.git /tmp/age \
    && cd /tmp/age \
    && make PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config \
    && make PG_CONFIG=/usr/lib/postgresql/16/bin/pg_config install \
    && rm -rf /tmp/age

FROM pgvector/pgvector:pg16

# Copy only the artifacts the running server needs.
COPY --from=age-builder /usr/lib/postgresql/16/lib/age.so \
                        /usr/lib/postgresql/16/lib/age.so
COPY --from=age-builder /usr/share/postgresql/16/extension/age* \
                        /usr/share/postgresql/16/extension/

# AGE must be in shared_preload_libraries (it registers planner hooks).
# We append to /etc/postgresql/postgresql.conf via the standard docker
# init helpers — the simplest path is to set it through the start command.
# Postgres 16's docker image honours POSTGRES_INITDB_ARGS but not
# arbitrary config knobs, so we drop a conf.d file that gets included.
# search_path keeps public FIRST: with ag_catalog first, any DB created
# without a per-database override (e.g. a fresh cvs_test) sends every
# unqualified CREATE TABLE — including alembic_version itself — into
# ag_catalog. Cypher only needs ag_catalog *present*, not first.
RUN mkdir -p /etc/postgresql/conf.d \
    && printf "shared_preload_libraries = 'age'\nsearch_path = '\"\$user\", public, ag_catalog'\n" \
       > /etc/postgresql/conf.d/age.conf

# Tell postgres to read that conf.d file. We piggyback on the official
# entrypoint's docker-ensure-initdb mechanism by mounting our config
# include via a postgresql.conf override. The cleanest portable way is
# via command flags; docker-compose already sets `command:` so we
# instead expose the conf via the image as a default include.
CMD ["postgres", \
     "-c", "shared_preload_libraries=age", \
     "-c", "search_path=\"$user\",public,ag_catalog"]
