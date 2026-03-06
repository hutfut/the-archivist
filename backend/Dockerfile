FROM python:3.12-slim AS build

WORKDIR /build

COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

WORKDIR /app

COPY --from=build /install /usr/local

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
