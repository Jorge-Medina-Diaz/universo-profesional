#!/usr/bin/env bash
# =============================================================================
# build-postgres-image.sh
# =============================================================================
# Build and publish the pre-built PostgreSQL + pgvector + Apache AGE image.
#
# Usage:
#   ./scripts/build-postgres-image.sh [--dry-run]
#
# Environment variables:
#   REGISTRY     — Docker registry (default: ghcr.io/<owner>)
#   IMAGE_NAME   — Image name    (default: cvs-postgres)
#   OWNER        — GHCR owner override (default: extracted from git remote,
#                  or $GITHUB_REPOSITORY_OWNER, or "local")
#
# Examples:
#   ./scripts/build-postgres-image.sh
#   REGISTRY=docker.io/myuser ./scripts/build-postgres-image.sh
#   ./scripts/build-postgres-image.sh --dry-run
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ---------------------------------------------------------------------------
# Resolve defaults
# ---------------------------------------------------------------------------
DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  echo "🟡 DRY RUN — images will be built and tagged but NOT pushed"
fi

# Try to infer owner from git remote, then env, then fallback
OWNER="${OWNER:-}"
if [ -z "$OWNER" ]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$REMOTE_URL" ]; then
      # Handles both https://github.com/owner/repo.git and git@github.com:owner/repo.git
      OWNER=$(echo "$REMOTE_URL" | sed -E 's|.*github.com[:/]||; s|/.*||; s|\.git$||')
    fi
  fi
fi
if [ -z "$OWNER" ] && [ -n "${GITHUB_REPOSITORY_OWNER:-}" ]; then
  OWNER="$GITHUB_REPOSITORY_OWNER"
fi
if [ -z "$OWNER" ]; then
  OWNER="local"
  echo "⚠️  Could not infer GHCR owner; using fallback '$OWNER'. Set OWNER=... to override."
fi

REGISTRY="${REGISTRY:-ghcr.io/${OWNER}}"
IMAGE_NAME="${IMAGE_NAME:-cvs-postgres}"

cd "${PROJECT_ROOT}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")
DATE_TAG=$(date +%Y%m%d)
TAG="${DATE_TAG}-${GIT_SHA}"

FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}"

echo "🔧 Building ${FULL_IMAGE}:${TAG} …"
echo "   Dockerfile: docker/postgres.Dockerfile"
echo "   Context:    ${PROJECT_ROOT}"

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
docker build \
  -f docker/postgres.Dockerfile \
  -t "${FULL_IMAGE}:${TAG}" \
  -t "${FULL_IMAGE}:latest" \
  "${PROJECT_ROOT}"

# Also tag with the PG16 flavour for backwards compatibility
docker tag "${FULL_IMAGE}:${TAG}" "${FULL_IMAGE}:pg16"

echo "✅ Built and tagged:"
echo "   ${FULL_IMAGE}:${TAG}"
echo "   ${FULL_IMAGE}:latest"
echo "   ${FULL_IMAGE}:pg16"

# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = "1" ]; then
  echo "🟡 Skipping push (--dry-run)"
  echo "   To push manually:"
  echo "     docker push ${FULL_IMAGE}:${TAG}"
  echo "     docker push ${FULL_IMAGE}:latest"
  echo "     docker push ${FULL_IMAGE}:pg16"
  exit 0
fi

echo "📤 Pushing to ${REGISTRY} …"
docker push "${FULL_IMAGE}:${TAG}"
docker push "${FULL_IMAGE}:latest"
docker push "${FULL_IMAGE}:pg16"

echo "✅ Done. Image available at:"
echo "   ${FULL_IMAGE}:${TAG}"
echo "   ${FULL_IMAGE}:latest"
echo "   ${FULL_IMAGE}:pg16"
