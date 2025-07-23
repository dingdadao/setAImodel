from fastapi import FastAPI
from . import routes
from .database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)  # 初始化表
app.include_router(routes.router)
