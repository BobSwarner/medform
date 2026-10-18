FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py

WORKDIR /srv/medform

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app
COPY wsgi.py docker-entrypoint.sh ./
RUN useradd --system --no-create-home medform && chmod +x docker-entrypoint.sh
USER medform

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
