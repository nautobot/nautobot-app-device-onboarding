ARG python_ver=3.7
FROM python:${python_ver}

# Set env vars that won't change per image
ENV PYTHONUNBUFFERED=1 \
    prometheus_multiproc_dir=/prom_cache \
    PATH="/root/.poetry/bin:$PATH"

RUN mkdir /prom_cache

RUN pip install --upgrade pip\
  && pip install poetry

# -------------------------------------------------------------------------------------
# Install Capacity Metrics Plugin and Nautobot
# -------------------------------------------------------------------------------------
WORKDIR /source

COPY . /source

RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi
