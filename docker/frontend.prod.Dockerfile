# Production-grade frontend image.
#
# Stage 1: build the SPA with Vite (incl. landing pre-render).
# Stage 2: serve dist/ with nginx + SPA fallback + security headers.
#
# Why nginx instead of `vite preview`: preview is for local development
# (single connection, no caching, no compression). nginx does gzip, sets
# long max-age on hashed assets, and forwards unknown routes to index.html
# so the SPA router takes over.

FROM node:22-bookworm-slim AS builder

ENV NODE_ENV=production \
    NPM_CONFIG_UPDATE_NOTIFIER=false

WORKDIR /build

# Copy manifests first so the layer cache survives source-only edits.
COPY frontend/package.json ./
RUN npm install --include=dev && npm install --include=dev @rollup/rollup-linux-x64-gnu @esbuild/linux-x64 --no-save

# Then the source tree.
COPY frontend/ .

# VITE_* env can be baked at build time via Docker build args. Fly.io etc.
# expose them with `--build-arg VITE_API_BASE_URL=...`.
ARG VITE_API_BASE_URL
ARG VITE_SENTRY_DSN
ARG VITE_STRIPE_PUBLIC_KEY
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_SENTRY_DSN=${VITE_SENTRY_DSN} \
    VITE_STRIPE_PUBLIC_KEY=${VITE_STRIPE_PUBLIC_KEY}

RUN npm run build && \
    (node scripts/prerender.mjs || echo "prerender step optional, skipping if missing")


FROM nginx:1.27-alpine AS runtime

# Drop privileges. The official nginx image already supports running as
# user `nginx` (UID 101) — we just need to make sure the writable paths
# are owned by that user so the worker processes can bind / write logs.
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d /run && \
    sed -i 's|pid /run/nginx.pid|pid /tmp/nginx.pid|' /etc/nginx/nginx.conf

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=nginx:nginx /build/dist /usr/share/nginx/html

# Listen on 8080 (non-privileged port — required when not running as root)
EXPOSE 8080

USER nginx

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
