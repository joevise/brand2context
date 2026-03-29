FROM node:20-alpine
WORKDIR /app
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install
COPY web/frontend/ .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
