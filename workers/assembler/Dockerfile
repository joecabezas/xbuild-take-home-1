FROM python:3.12-slim
WORKDIR /app
COPY shared /shared
RUN pip install --no-cache-dir -e /shared
COPY workers/assembler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY workers/assembler/ .
CMD ["python", "worker.py"]
