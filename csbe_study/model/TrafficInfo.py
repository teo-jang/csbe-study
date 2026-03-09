from dataclasses import dataclass, fields
from sqlalchemy import Column, Integer, Date, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


@dataclass
class TrafficInfo(Base):
    __tablename__ = "traffic_info"
    id: int
    transportation_date: str
    line_name: str
    external_station_code: str
    station_name: str
    division_name: str
    from_00_to_06: int
    from_06_to_07: int
    from_07_to_08: int
    from_08_to_09: int
    from_09_to_10: int
    from_10_to_11: int
    from_11_to_12: int
    from_12_to_13: int
    from_13_to_14: int
    from_14_to_15: int
    from_15_to_16: int
    from_16_to_17: int
    from_17_to_18: int
    from_18_to_19: int
    from_19_to_20: int
    from_20_to_21: int
    from_21_to_22: int
    from_22_to_23: int
    from_23_to_24: int
    from_24_to_end: int

    id = Column(Integer, primary_key=True)
    transportation_date = Column(Date)
    line_name = Column(String(50))
    external_station_code = Column(String(50))
    station_name = Column(String(50))
    division_name = Column(String(50))
    from_00_to_06 = Column(Integer)
    from_06_to_07 = Column(Integer)
    from_07_to_08 = Column(Integer)
    from_08_to_09 = Column(Integer)
    from_09_to_10 = Column(Integer)
    from_10_to_11 = Column(Integer)
    from_11_to_12 = Column(Integer)
    from_12_to_13 = Column(Integer)
    from_13_to_14 = Column(Integer)
    from_14_to_15 = Column(Integer)
    from_15_to_16 = Column(Integer)
    from_16_to_17 = Column(Integer)
    from_17_to_18 = Column(Integer)
    from_18_to_19 = Column(Integer)
    from_19_to_20 = Column(Integer)
    from_20_to_21 = Column(Integer)
    from_21_to_22 = Column(Integer)
    from_22_to_23 = Column(Integer)
    from_23_to_24 = Column(Integer)
    from_24_to_end = Column(Integer)

    def __str__(self):
        field_strings = [
            f"{field.name}={getattr(self, field.name)}" for field in fields(self)
        ]
        return ", ".join(field_strings)
