FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ENV NODE_ENV=production
ENV HOSTNAME="0.0.0.0"
ENV PORT=3099

RUN npm run build

EXPOSE 3099

CMD ["npm", "run", "start"]

