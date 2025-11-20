FROM node:20-bullseye-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci && \
    npm install lightningcss@latest && \
    npm install @tailwindcss/oxide-linux-arm64-gnu@latest || true

# Copy source code
COPY . .

# Build the application (disable lightningcss native issues if any)
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_DISABLE_LIGHTNINGCSS=1
ENV NEXT_DISABLE_TURBOPACK=1
ENV TAILWIND_DISABLE_OXIDE=1
ENV NEXT_DISABLE_TURBOPACK=1
ENV IN_DOCKER=1
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
