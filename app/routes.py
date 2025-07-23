from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import IPRequest
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
