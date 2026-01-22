# Python 3.11 베이스 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# MCP 서버 패키지 포함 (향후 추가될 디렉토리)
# COPY mcp_servers/ ./mcp_servers/

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 포트 8000 노출
EXPOSE 8000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# FastAPI 서버 시작
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
