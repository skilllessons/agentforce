# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
WORKDIR /workspace

FROM base AS deps
COPY pnpm-workspace.yaml package.json ./
COPY apps/studio/package.json apps/studio/
RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --filter @agentforge/studio... --prefer-offline

FROM deps AS build
COPY apps/studio ./apps/studio
WORKDIR /workspace/apps/studio
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /workspace/apps/studio/.next/standalone /app
COPY --from=build --chown=app:app /workspace/apps/studio/.next/static /app/apps/studio/.next/static
COPY --from=build --chown=app:app /workspace/apps/studio/public /app/apps/studio/public
USER app
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
  CMD wget -qO- http://127.0.0.1:3000/ || exit 1
CMD ["node", "apps/studio/server.js"]
