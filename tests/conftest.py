"""
Ch.21 - 테스트 공통 Fixture

Unit Test와 Integration Test에서 공유하는 fixture를 정의한다.
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


MYSQL_URL = "mysql+pymysql://root:csbe@localhost:3306/csbe_study"


@pytest.fixture
def db_session():
    """실제 DB 세션을 생성한다 (Integration Test용)"""
    engine = create_engine(MYSQL_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def setup_tables(db_session):
    """테스트용 테이블을 초기화한다"""
    db_session.execute(text("DROP TABLE IF EXISTS ch21_orders"))
    db_session.execute(text("DROP TABLE IF EXISTS ch21_products"))
    db_session.execute(
        text(
            """
        CREATE TABLE ch21_products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            stock INT NOT NULL DEFAULT 0,
            price INT NOT NULL DEFAULT 0
        )
    """
        )
    )
    db_session.execute(
        text(
            """
        CREATE TABLE ch21_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_name VARCHAR(100) NOT NULL,
            quantity INT NOT NULL,
            total_price INT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending'
        )
    """
        )
    )
    db_session.execute(
        text(
            "INSERT INTO ch21_products (name, stock, price) VALUES "
            "('노트북', 100, 1500000), ('키보드', 50, 150000)"
        )
    )
    db_session.commit()
    yield
