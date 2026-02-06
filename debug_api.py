import asyncio
import httpx
import os
import sys

# 设置环境
sys.path.append(os.getcwd())

async def debug():
    from main import app
    print("🛠️  开始 API 联调诊断...")
    
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1") as client:
        # 1. 获取 Token
        print("1. 尝试使用 admin 账户获取 Token...")
        from app.core.config import settings
        r = await client.post("/auth/token", data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD
        })
        
        if r.status_code != 200:
            print(f"❌ 登录失败 ({r.status_code}): {r.text}")
            return
        
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ 登录成功。")

        # 2. 获取任务配置
        print("
2. 请求 /tasks/configs ...")
        r = await client.get("/tasks/configs", headers=headers)
        print(f"状态码: {r.status_code}")
        print(f"返回数据: {r.text[:200]}...") # 只显示前200字符
        
        data = r.json()
        if data.get("success") and len(data.get("data", [])) > 0:
            print(f"✅ 成功获取到 {len(data['data'])} 个任务配置。")
        else:
            print("❓ 接口返回成功，但任务列表为空。")

if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("❌ 未发现 .env 文件。")
    else:
        asyncio.run(debug())
