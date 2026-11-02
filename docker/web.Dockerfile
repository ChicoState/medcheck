FROM node:22.14.0-bookworm-slim

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

WORKDIR /workspace/web

RUN corepack enable && corepack prepare pnpm@10.4.1 --activate

COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY web/ ./

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
