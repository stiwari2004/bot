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
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_DISABLE_TURBOPACK=1
ENV IN_DOCKER=1
ENV DOCKER=1
# FORCE empty - this is what gets baked into the JavaScript bundle
# Next.js will use relative URLs like /api/v1/... instead of http://...
ENV NEXT_PUBLIC_API_BASE_URL=""
# Verify it's empty before build (for debugging)
RUN echo "=== Build Environment Check ===" && \
    echo "NEXT_PUBLIC_API_BASE_URL (should be empty): '${NEXT_PUBLIC_API_BASE_URL}'" && \
    [ -z "${NEXT_PUBLIC_API_BASE_URL}" ] && echo "✓ NEXT_PUBLIC_API_BASE_URL is empty - good!" || echo "✗ WARNING: NEXT_PUBLIC_API_BASE_URL is not empty!" && \
    npm run build

EXPOSE 3000
CMD ["npm", "start"]
