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
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_DISABLE_TURBOPACK=1
ENV IN_DOCKER=1
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
