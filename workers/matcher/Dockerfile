FROM python:3.12-slim
WORKDIR /app

COPY shared ./shared
COPY workers/matcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the model into the image at build time so startup requires no download
ARG MATCHER_MODEL=all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${MATCHER_MODEL}')"

COPY workers/matcher/ .

CMD ["python", "worker.py"]
