import json

import httpx
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .cache import redis_client
from .database import SessionLocal
from .models import IPRequest, IPCache
from .tbag import calc_md5

router = APIRouter()


STATUS_PENDING = 0
STATUS_VALID = 1
STATUS_INVALID = 2
STATUS_BLOCKED = 3

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/log")
async def log_request(request: Request, db: Session = Depends(get_db)):
    data = await request.form()
    ip = data.get("ip","")
    ua = data.get("ua","")
    referer = data.get("referer","")
    url = data.get("url","")
    user_agent = data.get("user_agent", "")
    cookie = data.get("cookie", "")

    if not ip:
        return {"status": "pass"}
    if not ua:
        ua = user_agent


    server_md5 = calc_md5(ip, ua, referer, url)

    # 检查是否已存在相同的server_md5
    exists = db.query(IPRequest).filter_by(server_md5=server_md5).first()
    if exists:
        return {"status": "logged"}

    # 判断所有字段是否都有值
    entry_status = STATUS_PENDING
    if ip and ua and referer and cookie:
        entry_status = STATUS_VALID

    if ip and ua and referer:
        entry_status = STATUS_VALID
    
    if not referer and not cookie:
        entry_status = STATUS_BLOCKED


    entry = IPRequest(
        ip=ip,
        ua=ua,
        referer=referer,
        url=url,
        cookie=cookie,
        server_md5=server_md5,
        status=entry_status,
    )
    db.add(entry)
    db.commit()
    return {"status": "logged"}


@router.get("/ip")
async def ip_request(
    request: Request,
    ip: str = Query(..., description="要查询的IP地址"),
    db: Session = Depends(get_db)
):
    # Redis key
    redis_key = f"ip_cache:{ip}"

    # 1. 先查 Redis
    cached = await redis_client.get(redis_key)
    if cached:
        return {"code":200, **json.loads(cached)}

    # 2. 查数据库
    db_record = db.query(IPCache).filter(IPCache.ip == ip).first()
    if db_record:
        data = {
            "ip": db_record.ip,
            "country": db_record.country,
            "country_code": db_record.country_code,
            "prov": db_record.prov,
            "city": db_record.city,
            "city_code": db_record.city_code,
            "city_short_code": db_record.city_short_code,
            "area": db_record.area,
            "post_code": db_record.post_code,
            "area_code": db_record.area_code,
            "isp": db_record.isp,
            "lng": db_record.lng,
            "lat": db_record.lat,
            "long_ip": db_record.long_ip,
            "big_area": db_record.big_area,
        }

        # 回写 Redis 缓存，有效期 24 小时（可根据需求调整）
        await redis_client.set(redis_key, json.dumps(data), ex=86400)
        return {"code":200, **data}

    # 3. 请求 ip9.com.cn
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://ip9.com.cn/get?ip={ip}", timeout=5)
            response.raise_for_status()
            result = response.json().get("data", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"外部请求失败: {e}")

    if not result or "isp" not in result:
        raise HTTPException(status_code=400, detail="返回数据无效")

    # 4. 插入数据库
    record = IPCache(
        ip=result.get("ip"),
        country=result.get("country"),
        country_code=result.get("country_code"),
        prov=result.get("prov"),
        city=result.get("city"),
        city_code=result.get("city_code"),
        city_short_code=result.get("city_short_code"),
        area=result.get("area"),
        post_code=result.get("post_code"),
        area_code=result.get("area_code"),
        isp=result.get("isp"),
        lng=result.get("lng"),
        lat=result.get("lat"),
        long_ip=result.get("long_ip"),
        big_area=result.get("big_area"),
    )
    db.add(record)
    db.commit()

    # 5. 写入 Redis 缓存
    await redis_client.set(redis_key, json.dumps(result), ex=86400)

    return {"code":200, **result}