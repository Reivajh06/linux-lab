FROM node:24-bookworm-slim AS frontend
WORKDIR /build
RUN npm install -g pnpm@11.25.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN pnpm --filter linux-lab-ui install --frozen-lockfile
COPY frontend/ ./frontend/
RUN pnpm --dir frontend build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LAB_DATA_DIR=/data
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/
COPY courses/ /app/courses/
COPY EXERCISE_FORMAT.md /app/EXERCISE_FORMAT.md
COPY --from=frontend /build/frontend/dist /app/frontend/dist
WORKDIR /app/backend
EXPOSE 8080
CMD ["uvicorn", "lab.main:app", "--host", "0.0.0.0", "--port", "8080", "--ws-max-size", "8388608"]
