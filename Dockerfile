FROM python:2.7
MAINTAINER mcx_221@foxmail.com

ENV WORKDIR=/wecron
ENV VCAP_APP_PORT=8000

WORKDIR $WORKDIR

EXPOSE $VCAP_APP_PORT

HEALTHCHECK CMD curl --fail http://localhost:$VCAP_APP_PORT/?healthy || exit 1

RUN apt-get update
RUN apt-get install -y ffmpeg libavcodec-extra

# From https://fly.io/docs/blueprints/opensshd/
RUN apt-get update \
 && apt-get install -y openssh-server vim lsof \
 && cp /etc/ssh/sshd_config /etc/ssh/sshd_config-original \
 && sed -i 's/^#\s*Port.*/Port 2333/' /etc/ssh/sshd_config \
 && sed -i 's/^#\s*PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config \
 && mkdir -p /root/.ssh \
 && chmod 700 /root/.ssh \
 && mkdir /var/run/sshd \
 && chmod 755 /var/run/sshd \
 && rm -rf /var/lib/apt/lists /var/cache/apt/archives

COPY requirements.txt $WORKDIR
RUN pip install --no-cache-dir -r requirements.txt

COPY . $WORKDIR

#RUN make docs

CMD service ssh start && make run-in-prod