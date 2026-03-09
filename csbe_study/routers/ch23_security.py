"""
Ch.23 - 보안은 남의 일이 아니다

XSS, SQL Injection, IDOR 등 대표적인 웹 보안 취약점을 재현하고
방어 코드와 비교한다.
취약 버전과 안전 버전을 나란히 두어
"왜 위험한가"와 "어떻게 막는가"를 동시에 보여준다.
"""

import html

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


# ─────────────────────────────────────────
# MySQL 연결 (docker-compose.yml의 csbe-mysql 컨테이너)
# ─────────────────────────────────────────

MYSQL_URL = "mysql+pymysql://root:csbe@localhost:3306/csbe_study"

_engine = create_engine(
    MYSQL_URL,
    pool_size=10,
    max_overflow=5,
    pool_recycle=3600,
)
_Session = sessionmaker(bind=_engine)


# ─────────────────────────────────────────
# ORM 모델 정의 (inline)
# ─────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Ch23Post(Base):
    """게시글 테이블"""

    __tablename__ = "ch23_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(50), nullable=False)


class Ch23User(Base):
    """사용자 테이블"""

    __tablename__ = "ch23_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")


# ─────────────────────────────────────────
# 라우터 정의
# ─────────────────────────────────────────

router = APIRouter(prefix="/security", tags=["ch23-security"])


@router.post("/reset")
def reset_tables():
    """테이블 초기화 및 샘플 데이터 삽입"""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)

    session = _Session()
    try:
        # 샘플 게시글
        posts = [
            {
                "title": "FastAPI 시작하기",
                "content": "FastAPI는 빠르고 현대적인 Python 웹 프레임워크다.",
                "author": "admin",
            },
            {
                "title": "SQLAlchemy 기초",
                "content": "SQLAlchemy는 Python의 대표적인 ORM이다.",
                "author": "dev_kim",
            },
            {
                "title": "보안 테스트 가이드",
                "content": "웹 애플리케이션 보안 테스트의 기본을 다룬다.",
                "author": "security_team",
            },
            {
                "title": "Docker 입문",
                "content": "컨테이너 기술의 기본 개념과 사용법을 설명한다.",
                "author": "dev_lee",
            },
            {
                "title": "k6로 부하 테스트하기",
                "content": "k6를 활용한 성능 테스트 방법을 소개한다.",
                "author": "qa_park",
            },
        ]
        for p in posts:
            session.execute(
                text(
                    "INSERT INTO ch23_posts (title, content, author) "
                    "VALUES (:title, :content, :author)"
                ),
                p,
            )

        # 샘플 사용자
        users = [
            {"username": "admin", "email": "admin@csbe.dev", "role": "admin"},
            {"username": "dev_kim", "email": "kim@csbe.dev", "role": "developer"},
            {"username": "dev_lee", "email": "lee@csbe.dev", "role": "developer"},
            {"username": "user_park", "email": "park@csbe.dev", "role": "user"},
        ]
        for u in users:
            session.execute(
                text(
                    "INSERT INTO ch23_users (username, email, role) "
                    "VALUES (:username, :email, :role)"
                ),
                u,
            )

        session.commit()
        return {
            "message": "테이블 초기화 완료",
            "posts": len(posts),
            "users": len(users),
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# XSS (Cross-Site Scripting)
# ─────────────────────────────────────────


@router.get("/xss-vulnerable")
def xss_vulnerable(keyword: str = ""):
    """XSS 취약 엔드포인트: 사용자 입력을 그대로 HTML에 삽입한다

    keyword에 <script>alert('xss')</script> 를 넣으면
    브라우저에서 스크립트가 실행된다.
    """
    return HTMLResponse(
        f"""
    <html><body>
    <h1>검색 결과: {keyword}</h1>
    <p>'{keyword}'에 대한 검색 결과입니다.</p>
    </body></html>
    """
    )


@router.get("/xss-safe")
def xss_safe(keyword: str = ""):
    """XSS 방어 엔드포인트: html.escape()로 특수문자를 이스케이프한다

    <script> 태그가 &lt;script&gt;로 변환되어
    브라우저가 텍스트로 렌더링한다.
    """
    safe_keyword = html.escape(keyword)
    return HTMLResponse(
        f"""
    <html><body>
    <h1>검색 결과: {safe_keyword}</h1>
    <p>'{safe_keyword}'에 대한 검색 결과입니다.</p>
    </body></html>
    """
    )


# ─────────────────────────────────────────
# SQL Injection
# ─────────────────────────────────────────


@router.get("/sqli-vulnerable")
def sqli_vulnerable(keyword: str = ""):
    """SQL Injection 취약 엔드포인트: f-string으로 SQL을 조합한다

    공격 예시: keyword = "'; DROP TABLE ch23_posts; --"
    실제로 테이블이 삭제될 수 있다!
    """
    session = _Session()
    try:
        # 절대 이렇게 하면 안 된다!
        query = f"SELECT * FROM ch23_posts WHERE title LIKE '%{keyword}%'"
        results = session.execute(text(query)).fetchall()
        return {
            "query_used": query,  # 어떤 SQL이 실행됐는지 보여준다
            "results": [dict(r._mapping) for r in results],
            "warning": "이 엔드포인트는 SQL Injection에 취약하다!",
        }
    finally:
        session.close()


@router.get("/sqli-safe")
def sqli_safe(keyword: str = ""):
    """SQL Injection 방어 엔드포인트: 파라미터 바인딩을 사용한다

    :keyword 자리에 값이 바인딩되므로
    SQL 구조 자체를 변경할 수 없다.
    """
    session = _Session()
    try:
        query = text("SELECT * FROM ch23_posts WHERE title LIKE :kw")
        results = session.execute(query, {"kw": f"%{keyword}%"}).fetchall()
        return {
            "query_used": "SELECT * FROM ch23_posts WHERE title LIKE :kw (parameterized)",
            "results": [dict(r._mapping) for r in results],
            "defense": "파라미터 바인딩으로 SQL Injection 차단",
        }
    finally:
        session.close()


# ─────────────────────────────────────────
# IDOR (Insecure Direct Object Reference)
# ─────────────────────────────────────────


@router.get("/user/{user_id}")
def get_user_vulnerable(user_id: int):
    """IDOR 취약 엔드포인트: 인증/인가 없이 다른 사용자 정보를 조회한다

    user_id만 알면 누구의 정보든 볼 수 있다.
    인증(Authentication): 누구인가?
    인가(Authorization): 권한이 있는가?
    """
    session = _Session()
    try:
        row = session.execute(
            text("SELECT * FROM ch23_users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()
        if not row:
            return {"error": "사용자 없음"}
        return {
            "user": dict(row._mapping),
            "warning": "인증/인가 없이 아무 사용자 정보를 조회할 수 있다!",
        }
    finally:
        session.close()
