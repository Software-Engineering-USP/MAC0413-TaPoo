FROM node:22.22.0-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# O Vite embute VITE_API_URL no bundle durante o build, não em tempo de execução.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
