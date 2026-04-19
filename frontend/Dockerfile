FROM --platform=$BUILDPLATFORM node:22-bookworm-slim AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN corepack enable
RUN pnpm install --frozen-lockfile=false

COPY . .
RUN pnpm build

FROM --platform=linux/amd64 nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
