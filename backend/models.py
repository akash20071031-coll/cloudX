from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from database import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)

    evidence_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    filename = Column(String, nullable=False)

    file_path = Column(String, nullable=False)

    sha256_hash = Column(String, nullable=False)

    status = Column(
        String,
        default="VERIFIED"
    )

    uploaded_by = Column(
        String,
        default="Investigator"
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )