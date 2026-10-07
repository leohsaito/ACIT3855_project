from datetime import datetime, UTC
from sqlalchemy import BigInteger
from sqlalchemy import Integer, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class Attendance(Base):
    __tablename__ = "attendance"

    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    stadium_id = mapped_column(String(50), nullable=False)
    attendance = mapped_column(Integer, nullable=False)
    capacity = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(DateTime, nullable=False)

    recorded_timestamp = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC)
    )


class TicketSale(Base):
    __tablename__ = "ticket_sale"

    id = mapped_column(Integer, primary_key=True)
    trace_id = mapped_column(BigInteger, nullable=False)
    stadium_id = mapped_column(String(50), nullable=False)
    tickets_sold = mapped_column(Integer, nullable=False)
    ticket_price = mapped_column(Float, nullable=False)
    timestamp = mapped_column(DateTime, nullable=False)

    recorded_timestamp = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC)
    )