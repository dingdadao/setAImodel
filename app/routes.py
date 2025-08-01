import json

import httpx
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .cache import redis_client
from .database import SessionLocal
from .models import IPRequest, IPCache
from .tbag import calc_md5
import ipaddress

router = APIRouter()


STATUS_PENDING = 0
STATUS_VALID = 1
STATUS_INVALID = 2
STATUS_BLOCKED = 3 # 手动拒绝

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 支持多个网段
IP_WHITELIST = [
    ipaddress.ip_network("10.0.0.0/24"),
    ipaddress.ip_network("192.168.1.0/24"),
    ipaddress.ip_network("127.0.0.0/8"),
]

def is_ip_whitelisted(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        return any(ip_obj in net for net in IP_WHITELIST)
    except ValueError:
        return False  # 无效IP默认不跳过
@router.post("/log")
async def log_request(request: Request, db: Session = Depends(get_db)):
    data = await request.form()
    ip = data.get("ip","")
    ua = data.get("ua","")
    referer = data.get("referer","")
    url = data.get("url","")
    user_agent = data.get("user_agent", "")
    cookie = data.get("cookie", "")

    if not is_ip_whitelisted(ip):
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
    
    if not referer and not ua:
        entry_status = STATUS_INVALID


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


@router.get("/ip_stop")
async def ipStop_request(
    request: Request,
    ip: str = Query(..., description="要查询的IP地址"),
    db: Session = Depends(get_db)
):
    REDIS_PREFIX = "ipstop:"
    REDIS_TTL = 300
    # 1️⃣ 校验IP格式合法性
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        await redis_client.setex(f"{REDIS_PREFIX}{ip}", REDIS_TTL, "400")
        return {"code": 400, "msg": "非法IP地址"}

    # 2️⃣ 查询Redis缓存
    cache_key = f"{REDIS_PREFIX}{ip}"
    cached_code = await redis_client.get(cache_key)
    if cached_code:
        code = int(cached_code)
        msg = "非法IP地址" if code == 400 else ("需要校验" if code == 2198 else "")
        return {"code": code, "msg": msg}

    # 3️⃣ 查询数据库
    record = db.query(IPRequest).filter_by(ip=ip).order_by(IPRequest.id.desc()).first()

    # 4️⃣ 判断并设置缓存
    if not record:
        await redis_client.setex(cache_key, REDIS_TTL, 200)
        return {"code": 200, "msg": ""}

    if record.status == STATUS_BLOCKED:
        await redis_client.setex(cache_key, REDIS_TTL, 2199)
        return {"code": 2199, "msg": ""}

    if record.status == STATUS_INVALID:
        await redis_client.setex(cache_key, REDIS_TTL, 2198)
        return {"code": 2198, "msg": "系统错误..."}

    await redis_client.setex(cache_key, REDIS_TTL, 200)
    return {"code": 200, "msg": ""}