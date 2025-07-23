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

    print(f"收到数据: ip={ip}, ua={ua}, referer={referer}, url={url}, user_agent={user_agent}, cookie={cookie}")

    server_md5 = calc_md5(ip, ua, referer, url)
    print(f"生成的server_md5: {server_md5}")

    # 判断所有字段是否都有值
    entry_status = STATUS_PENDING
    if ip and ua and referer and cookie:
        print("命中: ip, ua, referer, cookie 都有，status=STATUS_VALID")
        entry_status = STATUS_VALID

    if ip and ua and referer:
        print("命中: ip, ua, referer 都有，status=STATUS_VALID")
        entry_status = STATUS_VALID
    
    if not referer and not cookie:
        print("命中: referer和cookie都没有，status=STATUS_BLOCKED")
        entry_status = STATUS_BLOCKED

    print(f"最终写入status: {entry_status}")

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
    print(f"写入数据库: id={entry.id}, status={entry.status}")
    return {"status": "logged"}
