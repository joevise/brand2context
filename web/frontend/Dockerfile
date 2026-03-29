FROM node:20-alpine
WORKDIR /app
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install
COPY web/frontend/ .
ARG NEXT_PUBLIC_API_URL=http://67.209.190.54:8004
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
