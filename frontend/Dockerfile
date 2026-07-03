# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve static files with Nginx
FROM nginx:alpine

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration if needed, otherwise default Nginx config works
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
