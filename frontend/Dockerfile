FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm install

COPY . .

# Optional build-time API base URL for Vite (e.g. http://localhost:8000).
# If you leave it empty, the app will use same-origin `/api` via Nginx.
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

