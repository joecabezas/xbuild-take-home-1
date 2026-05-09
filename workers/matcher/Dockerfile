FROM python:3.12-slim
WORKDIR /app
COPY shared /shared
RUN pip install --no-cache-dir -e /shared
COPY workers/matcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY workers/matcher/ .
CMD ["python", "worker.py"]
