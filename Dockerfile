FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV QCM_DEPLOY_TARGET=hf-space
ENV PYTHONPATH=/app/packages/domain/src:/app/packages/shared/src:/app/packages/application/src:/app/packages/infrastructure/src:/app/packages/observability/src:/app/apps/api/src

WORKDIR /app

COPY pyproject.toml README.md ./
COPY packages ./packages
COPY apps/api ./apps/api

RUN pip install --no-cache-dir -e .

EXPOSE 7860

CMD ["uvicorn", "qcm_api.main:app", "--host", "0.0.0.0", "--port", "7860"]
