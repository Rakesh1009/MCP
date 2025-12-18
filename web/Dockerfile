FROM node:20-slim

WORKDIR /app

# Install dependencies (better caching)
# We need to copy package files first
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source
COPY . .

# Start in dev mode
CMD ["npm", "run", "dev"]
