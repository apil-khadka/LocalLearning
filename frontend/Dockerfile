FROM node:22.21.0-alpine AS build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY docs/KOLIBRI_GUIDE.md ./docs/KOLIBRI_GUIDE.md
RUN npm run build

FROM nginx:1.28.0-alpine
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf
COPY deployment/20-runtime-config.sh /docker-entrypoint.d/20-runtime-config.sh
COPY --from=build /build/dist /usr/share/nginx/html
RUN chmod +x /docker-entrypoint.d/20-runtime-config.sh
EXPOSE 8080 8081
