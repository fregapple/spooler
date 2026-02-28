FROM python:3.12-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY bootstrap.sh /bootstrap.sh
RUN chmod +x /bootstrap.sh

ENTRYPOINT ["/bootstrap.sh"]