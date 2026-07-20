FROM python:3.13-slim

RUN pip install uv --quiet

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY sitebox/ sitebox/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "sitebox.app:app", "--host", "0.0.0.0", "--port", "8000"]
