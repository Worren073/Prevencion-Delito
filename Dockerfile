FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates xz-utils && \
    curl -sSfL https://get.tur.so/install.sh | sh && \
    mv /root/.turso/turso /usr/local/bin/turso && \
    rm -rf /root/.turso && \
    apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY db.py .
COPY templates/ ./templates/
COPY src/dashboard.html ./src/dashboard.html
RUN mkdir -p /app/data
EXPOSE 5000
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} app:app
