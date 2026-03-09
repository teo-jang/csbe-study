"""
Ch.16 - DB 성능 튜닝: 시드 데이터 삽입 스크립트

ch16_orders 테이블에 10만 건의 시드 데이터를 삽입한다.
FastAPI 서버 없이 독립 실행할 수 있다.

사용법:
    python scripts/seed_ch16.py

주의: docker-compose.yml의 MySQL 컨테이너가 실행 중이어야 한다.
"""

import random
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ─────────────────────────────────────────
# MySQL 연결 정보
# ─────────────────────────────────────────

MYSQL_URL = "mysql+pymysql://root:csbe@localhost:3306/csbe_study"

engine = create_engine(
    MYSQL_URL,
    pool_size=5,
    pool_recycle=3600,
)

Session = sessionmaker(bind=engine)


# ─────────────────────────────────────────
# 시드 데이터용 상수
# ─────────────────────────────────────────

PRODUCT_TITLES = [
    "맥북 프로 14인치",
    "삼성 갤럭시 S24",
    "아이패드 에어",
    "로지텍 MX Keys",
    "소니 WH-1000XM5",
    "LG 울트라와이드 모니터",
    "애플 매직 마우스",
    "레노버 씽크패드",
    "다이슨 에어랩",
    "닌텐도 스위치",
    "에어팟 프로 2세대",
    "삼성 오디세이 모니터",
    "키크론 K8 프로",
    "라즈베리 파이 5",
    "아이폰 15 프로",
]


def create_table():
    """ch16_orders 테이블을 생성한다 (기존 테이블은 삭제)"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ch16_orders"))
        conn.execute(
            text(
                "CREATE TABLE ch16_orders ("
                "  id INT AUTO_INCREMENT PRIMARY KEY,"
                "  user_id INT NOT NULL,"
                "  product_title VARCHAR(200) NOT NULL,"
                "  amount INT NOT NULL,"
                "  created_at DATETIME NOT NULL,"
                "  INDEX idx_ch16_created_id (created_at DESC, id DESC)"
                ")"
            )
        )
        conn.commit()
    print("테이블 생성 완료: ch16_orders")


def seed_data():
    """10만 건의 시드 데이터를 1000건씩 배치로 삽입한다"""
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    total_seconds = int((now - one_year_ago).total_seconds())
    total_rows = 100000
    batch_size = 1000

    session = Session()
    try:
        for batch_start in range(0, total_rows, batch_size):
            rows = []
            for _ in range(batch_size):
                random_seconds = random.randint(0, total_seconds)
                created_at = one_year_ago + timedelta(seconds=random_seconds)
                rows.append(
                    {
                        "user_id": random.randint(1, 5000),
                        "product_title": random.choice(PRODUCT_TITLES),
                        "amount": random.randint(10000, 2000000),
                        "created_at": created_at,
                    }
                )

            session.execute(
                text(
                    "INSERT INTO ch16_orders "
                    "(user_id, product_title, amount, created_at) "
                    "VALUES (:user_id, :product_title, :amount, :created_at)"
                ),
                rows,
            )

            # 진행률 출력
            inserted = batch_start + batch_size
            print(f"  삽입 완료: {inserted:,} / {total_rows:,}")

        session.commit()
        print(f"시드 데이터 삽입 완료: 총 {total_rows:,}건")
    except Exception as e:
        session.rollback()
        print(f"에러 발생: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Ch.16 시드 데이터 삽입 스크립트")
    print("=" * 50)
    create_table()
    seed_data()
    print("완료!")
