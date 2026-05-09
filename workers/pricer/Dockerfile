FROM python:3.12-slim
WORKDIR /app
COPY shared /shared
RUN pip install --no-cache-dir -e /shared
COPY workers/pricer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY workers/pricer/ .
CMD ["python", "worker.py"]
