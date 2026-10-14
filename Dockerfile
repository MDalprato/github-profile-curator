FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN useradd --uid 10001 --create-home curator
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=curator:curator app ./app
RUN mkdir -p /data && chown curator:curator /data
USER curator
CMD ["python", "-m", "app.main"]
