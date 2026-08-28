FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hub ./hub
COPY core ./core
COPY needles ./needles
COPY config ./config

CMD ["python", "-m", "hub.main"]
