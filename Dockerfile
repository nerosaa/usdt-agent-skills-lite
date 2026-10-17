FROM python:3.12-slim
WORKDIR /app
COPY mcp-usdt-payment-check/ /app/
ENV PYTHONUNBUFFERED=1
CMD ["python3", "server.py"]
