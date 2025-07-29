from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, BigInteger
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

class IPCache(Base):
    __tablename__ = "ip_cache"

    ip = Column(String(45), primary_key=True, index=True)
    country = Column(String(64))
    country_code = Column(String(10))
    prov = Column(String(64))
    city = Column(String(64))
    city_code = Column(String(64))
    city_short_code = Column(String(64))
    area = Column(String(64))
    post_code = Column(String(20))
    area_code = Column(String(20))
    isp = Column(String(128))
    lng = Column(String(32))         # 如果想支持小数精度可用 Float
    lat = Column(String(32))
    long_ip = Column(BigInteger)
    big_area = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)