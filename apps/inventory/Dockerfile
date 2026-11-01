# inventory — Node/Express, non-root (node:alpine ships uid 1000 'node').
FROM node:20-alpine
WORKDIR /app
COPY package.json .
RUN npm install --omit=dev
COPY index.js .
USER node
EXPOSE 8080
CMD ["node", "index.js"]
