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
RUN npm ci

# Copy source code
COPY . .

# Rebuild native modules for the correct platform (lightningcss needs this)
RUN npm rebuild || true

# Build the application
# CRITICAL: NEXT_PUBLIC_API_BASE_URL must be empty for relative URLs (nginx handles proxying)
# Accept build arg but force to empty if not provided or if it has a value
ARG NEXT_PUBLIC_API_BASE_URL
# Optional: set to /app for resolvify.tech/app so all assets are under /app (no separate /_next/ proxy needed)
ARG NEXT_PUBLIC_BASE_PATH
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_DISABLE_TURBOPACK=1
ENV IN_DOCKER=1
ENV DOCKER=1
# FORCE empty - this is what gets baked into the JavaScript bundle
ENV NEXT_PUBLIC_API_BASE_URL=""
# Pass through base path if provided (e.g. /app for resolvify.tech)
ENV NEXT_PUBLIC_BASE_PATH=${NEXT_PUBLIC_BASE_PATH}
RUN echo "=== Build Environment Check ===" && \
    echo "NEXT_PUBLIC_API_BASE_URL (should be empty): '${NEXT_PUBLIC_API_BASE_URL}'" && \
    echo "NEXT_PUBLIC_BASE_PATH: '${NEXT_PUBLIC_BASE_PATH}'" && \
    npm run build

EXPOSE 3000
CMD ["npm", "start"]
