FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY consilium ./consilium

RUN pip install --no-cache-dir -e ".[server,stream]"

EXPOSE 8000

# Default: run the API. Override the command to run the FastStream worker:
#   docker run ... faststream run consilium.messaging.streams:app
CMD ["uvicorn", "consilium.service.api:app", "--host", "0.0.0.0", "--port", "8000"]
