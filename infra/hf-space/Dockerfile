FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV QCM_DEPLOY_TARGET=hf-space

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/worker ./apps/worker

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "qcm_worker.main"]
