# syntax=docker/dockerfile:1.7
# Build context: apps/studio (the studio is a standalone npm project).
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM deps AS build
COPY . .
# Next.js bakes NEXT_PUBLIC_* in at build time (next.config.js rewrites).
# Staging passes the in-cluster Service: http://agentforge-api-gateway
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /app/.next/standalone /app
COPY --from=build --chown=app:app /app/.next/static /app/.next/static
COPY --from=build --chown=app:app /app/public /app/public
USER app
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s \
  CMD wget -qO- http://127.0.0.1:3000/ || exit 1
CMD ["node", "server.js"]
