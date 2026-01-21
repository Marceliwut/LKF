ARG CACHEBUST=2
FROM python:3.9

# FORCE CACHE BUST


WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

CMD ["gunicorn", "--config", "gunicorn-cfg.py", "core.wsgi"]
