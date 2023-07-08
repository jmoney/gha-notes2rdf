FROM alpine:3.12

ADD main.py /app/main.py
ADD requirements.txt /app/requirements.txt
COPY bin /app/bin

RUN apk add --no-cache python3 py3-pip
RUN pip install -r /app/requirements.txt

ENTRYPOINT [ "/app/bin/entrypoint.sh" ]