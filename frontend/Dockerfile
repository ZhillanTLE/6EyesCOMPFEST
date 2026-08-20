# Windfall console — Next.js 16, standalone output.
#
# Multi-stage so the runtime image carries no toolchain and no dev
# dependencies: only the traced server, the static assets and the public dir.

# ── deps ─────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# ── build ────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./

# The rewrite destination is BAKED INTO THE BUILD. next.config.ts calls
# rewrites() at build time and the result is written into
# .next/routes-manifest.json, so this cannot be a runtime environment variable
# -- setting it in docker-compose `environment:` would have no effect. It is a
# build arg, and changing the backend host means rebuilding the image.
ARG WINDFALL_API_ORIGIN=http://backend:8000
ENV WINDFALL_API_ORIGIN=${WINDFALL_API_ORIGIN}

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── runtime ──────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S -g 1001 nodejs && adduser -S -u 1001 -G nodejs nextjs

# The standalone output does NOT include `public/` or `.next/static` -- the
# Next docs are explicit that these are expected to be served by a CDN and must
# be copied manually otherwise. Omitting them yields an unstyled page with
# missing agent avatars, which is a confusing way to fail.
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/recovery',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
