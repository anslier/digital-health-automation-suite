FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

WORKDIR /workspace

COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
COPY backend/tests ./backend/tests

RUN cd backend && pip install --no-cache-dir '.[test]'

COPY system-tests ./system-tests

ENV PYTHONPATH=/workspace/backend

CMD ["pytest", "-q", "backend/tests", "system-tests"]
