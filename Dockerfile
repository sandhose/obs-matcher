FROM python:3-alpine

WORKDIR /app

RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python setup.py install
RUN python setup.py develop

ENV PYTHONUNBUFFERED=1 PYTHONHASHSEED=random PYTHONDONTWRITEBYTECODE=1

EXPOSE 5000

CMD [ "matcher", "run" ]
