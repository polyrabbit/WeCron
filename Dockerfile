FROM python:3.12-slim AS builder

# uWSGI is built from source, pcre2/zlib back its `route` and `http-auto-gzip` options
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpcre2-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /requirements.txt


FROM python:3.12-slim
LABEL maintainer="mcx_221@foxmail.com"

ENV WORKDIR=/wecron
ENV VCAP_APP_PORT=8000

WORKDIR $WORKDIR

EXPOSE $VCAP_APP_PORT

HEALTHCHECK CMD curl --fail http://localhost:$VCAP_APP_PORT/?healthy || exit 1

# From https://fly.io/docs/blueprints/opensshd/
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libavcodec-extra curl make libpcre2-8-0 openssh-server vim lsof \
 && cp /etc/ssh/sshd_config /etc/ssh/sshd_config-original \
 && sed -i 's/^#\s*Port.*/Port 2333/' /etc/ssh/sshd_config \
 && sed -i 's/^#\s*PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config \
 && mkdir -p /root/.ssh \
 && chmod 700 /root/.ssh \
 && mkdir -p /var/run/sshd \
 && chmod 755 /var/run/sshd \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index /wheels/* && rm -rf /wheels

COPY . $WORKDIR

#RUN make docs

CMD service ssh start && make run-in-prod
