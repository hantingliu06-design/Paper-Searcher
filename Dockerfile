FROM python:3.12-slim
WORKDIR /app
COPY scholar_compass ./scholar_compass
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "scholar_compass", "serve", "--host", "0.0.0.0"]
