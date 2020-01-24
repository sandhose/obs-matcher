FROM python:3.6-alpine

WORKDIR /app

RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev libffi-dev

RUN apk add --no-cache tzdata
RUN cp /usr/share/zoneinfo/Europe/Paris /etc/localtime
RUN echo "Europe/Paris" >  /etc/timezone

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

RUN python setup.py install
RUN python setup.py develop

RUN mkdir -p instance && chmod 777 instance

ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=random PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

CMD [ "matcher", "run" ]
