from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class ResponseModel(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "操作成功"

def resp_ok(data: Any = None, message: str = "操作成功") -> dict:
    return {"success": True, "data": data, "message": message}

def resp_err(message: str = "操作失败", data: Any = None) -> dict:
    return {"success": False, "data": data, "message": message}
