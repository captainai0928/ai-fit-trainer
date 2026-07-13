FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 최소화 — 순수 Python, 외부 API 의존 없음
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rules.py server.py ./

# 비루트 유저로 실행
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

CMD ["python", "server.py"]
