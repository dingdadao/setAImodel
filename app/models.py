from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from .database import Base

class IPRequest(Base):
    __tablename__ = "ip_requests"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), unique=True, nullable=False)
    ua = Column(String(255))
    referer = Column(String(1024))
    url = Column(String(1024))
    user_agent = Column(String(255))
    cookie = Column(String(2048))
    server_md5 = Column(String(64), unique=True, index=True)
    status = Column(Integer, default=0)

