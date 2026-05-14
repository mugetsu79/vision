FROM --platform=$BUILDPLATFORM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN corepack enable
RUN pnpm install --frozen-lockfile=false

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY config.template.js /etc/vezor/frontend/config.template.js
COPY docker-entrypoint.d/10-vezor-config.sh /docker-entrypoint.d/10-vezor-config.sh
RUN chmod +x /docker-entrypoint.d/10-vezor-config.sh

EXPOSE 8080
