from sqlalchemy import Column, String, Integer, DateTime, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from db.config.db import Base

class Shares(Base):
    __tablename__ = "shares"

    id=Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    folio_id=Column(String)
    company = Column(String)
    name = Column(String, nullable=False)
    father_name = Column(String)
    address = Column(String)
    pin_code = Column(Integer)
    number_of_shares = Column(Integer)
    net_dividend = Column(Numeric(10, 2))
    war_no = Column(Integer)
    chq_no = Column(Integer)
    dp_id = Column(String)
    year = Column(Integer)
    date_of_transfer = Column(Date)
    created_at = Column(
        DateTime,
        default = datetime.now
    ) 
    updated_at = Column(
        DateTime,
        default = datetime.now
    )
    deleted_at = Column(DateTime)