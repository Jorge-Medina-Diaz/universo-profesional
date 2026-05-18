FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json ./
RUN npm install --legacy-peer-deps

COPY . /app

EXPOSE 4000

CMD ["npm", "run", "start"]
