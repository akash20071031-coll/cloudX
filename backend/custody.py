from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from database import Base


class CustodyEvent(Base):
    __tablename__ = "custody_events"

    id = Column(Integer, primary_key=True, index=True)

    evidence_id = Column(String, nullable=False, index=True)

    from_user = Column(String, nullable=False)

    to_user = Column(String, nullable=False)

    action = Column(String, nullable=False)

    notes = Column(String, nullable=True)

    timestamp = Column(
        DateTime,
        default=datetime.utcnow
    )