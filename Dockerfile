FROM python:2.7
MAINTAINER mcx_221@foxmail.com

ENV WORKDIR=/wecron
ENV VCAP_APP_PORT=8000

WORKDIR $WORKDIR

EXPOSE $VCAP_APP_PORT

HEALTHCHECK CMD curl --fail http://localhost:$VCAP_APP_PORT/?healthy || exit 1

COPY requirements.txt $WORKDIR
RUN pip install --no-cache-dir -r requirements.txt

COPY . $WORKDIR

#RUN make docs

CMD ["make", "run-in-prod"]