FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt /app/requirements-base.txt
COPY api/requirements.txt /app/requirements-api.txt

RUN pip install --no-cache-dir -r requirements-base.txt -r requirements-api.txt

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
