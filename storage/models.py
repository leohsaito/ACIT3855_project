from datetime import datetime, UTC

from sqlalchemy import BigInteger, Integer, String, Float
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.dialects.mysql import TIMESTAMP


class Base(DeclarativeBase):
    pass


class Attendance(Base):
    __tablename__ = "attendance"

    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    stadium_id = mapped_column(String(50), nullable=False)
    attendance = mapped_column(Integer, nullable=False)
    capacity = mapped_column(Integer, nullable=False)

    timestamp = mapped_column(
        TIMESTAMP(fsp=6),
        nullable=False
    )

    recorded_timestamp = mapped_column(
        TIMESTAMP(fsp=6),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    def to_json(self):
        return {
            "trace_id": self.trace_id,
            "stadium_id": self.stadium_id,
            "attendance": self.attendance,
            "capacity": self.capacity,
            "timestamp": self.timestamp.isoformat(),
            "recorded_timestamp": self.recorded_timestamp.isoformat()
        }


class TicketSale(Base):
    __tablename__ = "ticket_sale"

    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    stadium_id = mapped_column(String(50), nullable=False)
    tickets_sold = mapped_column(Integer, nullable=False)
    ticket_price = mapped_column(Float, nullable=False)

    timestamp = mapped_column(
        TIMESTAMP(fsp=6),
        nullable=False
    )

    recorded_timestamp = mapped_column(
        TIMESTAMP(fsp=6),
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    def to_json(self):
        return {
            "trace_id": self.trace_id,
            "stadium_id": self.stadium_id,
            "tickets_sold": self.tickets_sold,
            "ticket_price": self.ticket_price,
            "timestamp": self.timestamp.isoformat(),
            "recorded_timestamp": self.recorded_timestamp.isoformat()
        }