# Stage 1: Build React UI
FROM node:20-alpine AS ui-builder
WORKDIR /build
COPY src/ui/package*.json ./
RUN npm ci
COPY src/ui/ ./
RUN npm run build

# Stage 2: Python API + static files
FROM python:3.12-slim
WORKDIR /app
COPY src/api/pyproject.toml ./
RUN pip install --no-cache-dir .
COPY src/api/ ./
COPY --from=ui-builder /build/dist ./static
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
