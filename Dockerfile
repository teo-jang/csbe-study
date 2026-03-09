# Ch.22 - 컨테이너 기술의 밑바닥
# Python 3.12 + Poetry 기반 FastAPI 서버
#
# 빌드: docker build -t csbe-study .
# 실행: docker run -p 8000:8000 csbe-study

FROM python:3.12-slim

# Poetry 설치
RUN pip install --no-cache-dir poetry==1.8.3

WORKDIR /app

# 의존성 파일만 먼저 복사 (Docker 레이어 캐시 활용)
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# 소스 코드 복사
COPY csbe_study/ ./csbe_study/

# FastAPI 서버 실행
# main.py의 import가 상대 경로이므로 csbe_study/ 디렉토리에서 실행
WORKDIR /app/csbe_study
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
