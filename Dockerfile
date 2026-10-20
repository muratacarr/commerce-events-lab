# One image definition for the three lab services; select with --build-arg SERVICE=<name>.
# Application code does not exist yet (milestones L1+), so the default command exits non-zero.
FROM python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

ARG SERVICE
RUN case "${SERVICE}" in order|payment|inventory) ;; *) echo "SERVICE must be order, payment or inventory" >&2; exit 1 ;; esac

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements.lock ./
RUN pip install --require-hashes --no-deps -r requirements.lock

COPY src/contracts ./contracts
COPY src/${SERVICE} ./${SERVICE}

USER 10001
ENV SERVICE=${SERVICE}
CMD ["python", "-c", "raise SystemExit('no application code yet: milestone L1 onward')"]
