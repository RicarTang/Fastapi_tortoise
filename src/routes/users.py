from fastapi import APIRouter, HTTPException, Depends,UploadFile
from fastapi.encoders import jsonable_encoder
from src.models import User_Pydantic, Login_pydantic, Users
from tortoise.contrib.fastapi import HTTPNotFoundError
from .. import schemas
from ..utils.log_util import log
from ..utils import security_util
from passlib.hash import md5_crypt
from ..utils import exceptions_util as exception
from ..utils import security_util
from datetime import timedelta
from typing import Optional
from fastapi.security import OAuth2PasswordRequestForm

user_route = APIRouter()


@user_route.get("/users", summary="获取所有用户", response_model=schemas.UsersOut)
async def get_users(limit: Optional[int] = 10, offset: Optional[int] = 0):
    """获取所有用户."""
    result = await User_Pydantic.from_queryset(
        Users.all().offset(offset).limit(limit))
    return schemas.UsersOut(data=result)


@user_route.get('/me', summary="获取当前用户", response_model=schemas.UserPy)
async def get_current_user(current_user: schemas.UserPy = Depends(
    security_util.get_current_user)):
    """获取当前用户"""
    return current_user


@user_route.post("/create", summary="创建用户", response_model=schemas.UserOut)
async def create_user(user: schemas.UserIn):
    """创建用户."""
    user.password = md5_crypt.hash(user.password)
    user_obj = await Users.create(**user.dict(exclude_unset=True))
    log.info(f"成功创建用户：{user.dict(exclude_unset=True)}")
    return schemas.UserOut(data=user_obj)


@user_route.get("/get/{user_id}",
                response_model=schemas.UserOut,
                summary="查询用户",
                responses={404: {
                    "model": HTTPNotFoundError
                }})
async def get_user(user_id: int):
    """查询单个用户."""
    log.debug(f"{await Users.get(id=user_id).values()}")
    # return await User_Pydantic.from_queryset_single(Users.get(id=user_id))
    user = await Users.get(id=user_id)
    return schemas.UserOut(data=user)


@user_route.put("/update/{user_id}",
                response_model=schemas.UserOut,
                summary="更新用户",
                responses={404: {
                    "model": HTTPNotFoundError
                }})
async def update_user(user_id: int, user: schemas.UserIn):
    """更新用户信息."""
    user.password = md5_crypt.hash(user.password)
    result = await Users.filter(id=user_id
                                ).update(**user.dict(exclude_unset=True))
    log.debug(f"update更新{result}条数据")
    return schemas.UserOut(data=await Users.get(id=user_id))


@user_route.delete("/delete/{user_id}",
                   response_model=schemas.Status,
                   summary="删除用户",
                   responses={404: {
                       "model": HTTPNotFoundError
                   }})
async def delete_user(user_id: int):
    """删除用户."""
    deleted_count = await Users.filter(id=user_id).delete()
    log.debug("")
    if not deleted_count:
        raise HTTPException(status_code=404,
                            detail=f"User {user_id} not found")
    return schemas.Status(message=f"Deleted user {user_id}")


@user_route.post("/login", summary="登录", response_model=schemas.Login)
# async def login(user: schemas.LoginIn):
async def login(user: OAuth2PasswordRequestForm = Depends()):
    """用户登陆."""
    # try:
    #     # query_user = await Login_pydantic.from_tortoise_orm(
    #     #     await Users.filter(username=user.username).first())

    # except AttributeError as e:
    #     log.debug(f"查询数据库用户错误:{e}")
    #     raise exception.ResponseException(content="Object does not exist!")
    # 查询数据库有无此用户
    query_user = await Login_pydantic.from_tortoise_orm(
        await Users.get(username=user.username))
    # 序列化Pydantic对象
    db_user = jsonable_encoder(query_user)
    # 验证密码
    if not md5_crypt.verify(secret=user.password, hash=query_user.password):
        raise exception.ResponseException(content="Password Error!")
    # jwt失效时间
    access_token_expires = timedelta(
        minutes=security_util.ACCESS_TOKEN_EXPIRE_MINUTES)
    # 创建jwt
    access_token = security_util.create_access_token(
        data={"sub": query_user.username}, expires_delta=access_token_expires)
    # db_user["access_token"] = access_token
    return schemas.Login(data=db_user,
                         access_token=access_token,
                         token_type="bearer")

@user_route.post('/uploadfile')
async def uploadfile(file:UploadFile):
    with open(f"./src/static/{file.filename}",'wb') as f:
        f.write(await file.read())
    
    return {"filename":file.filename}