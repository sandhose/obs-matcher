FROM python:3-alpine

RUN apk add --no-cache gcc python3-dev musl-dev libxslt-dev libffi-dev openssl-dev

RUN pip install --no-cache-dir scrapyd

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./scrapyd.conf /etc/scrapyd/
VOLUME /etc/scrapyd/ /var/lib/scrapyd/
EXPOSE 6800

CMD ["scrapyd"]
