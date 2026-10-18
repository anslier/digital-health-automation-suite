FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/angular.json frontend/tsconfig*.json frontend/proxy.conf.json ./
COPY frontend/src ./src
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/healthlink /usr/share/nginx/html
EXPOSE 80
