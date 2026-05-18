FROM node:22-bookworm-slim

WORKDIR /app

# Copy manifest first for layer caching
COPY package.json package-lock.json* ./

RUN npm install --include=dev

COPY . /app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
