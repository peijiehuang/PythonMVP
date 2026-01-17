import requests
import sys

BASE_URL = "http://localhost:8000"

def log(msg, success=True):
    icon = "[OK]" if success else "[FAIL]"
    print(f"{icon} {msg}")

def test_auth_flow():
    print("[INFO] 开始鉴权流程测试...")

    # 1. 测试公开接口 (Read Items)
    try:
        r = requests.get(f"{BASE_URL}/items/")
        if r.status_code == 200:
            log("公开接口 /items/ 访问成功")
        else:
            log(f"公开接口访问失败: {r.status_code}", False)
            return
    except Exception as e:
        log(f"服务未启动或连接失败: {e}", False)
        return

    # 2. 测试未登录创建物品 (期望 401)
    try:
        r = requests.post(f"{BASE_URL}/items/", json={"name": "Hacker Item"})
        if r.status_code == 401:
            log("未登录保护生效 (401 Unauthorized)")
        else:
            log(f"未登录保护失效: {r.status_code}", False)
    except Exception as e:
        log(f"请求异常: {e}", False)

    # 3. 登录获取 Token
    token = None
    try:
        # OAuth2PasswordRequestForm expects form data
        data = {"username": "admin", "password": "admin"} 
        r = requests.post(f"{BASE_URL}/token", data=data)
        if r.status_code == 200:
            token = r.json()["access_token"]
            log(f"登录成功，获取 Token: {token[:10]}...")
        else:
            log(f"登录失败: {r.text}", False)
            return
    except Exception as e:
        log(f"登录请求异常: {e}", False)
        return

    # 4. 测试带 Token 创建物品
    item_id = None
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = requests.post(f"{BASE_URL}/items/", json={"name": "Secure Item", "description": "Created by Admin"}, headers=headers)
            if r.status_code == 200:
                item_data = r.json()
                item_id = item_data["id"]
                log(f"带 Token 创建物品成功: ID {item_id}")
            else:
                log(f"带 Token 创建物品失败: {r.status_code} {r.text}", False)
        except Exception as e:
            log(f"创建请求异常: {e}", False)

    # 5. 清理测试数据
    if token and item_id:
        headers = {"Authorization": f"Bearer {token}"}
        try:
            r = requests.delete(f"{BASE_URL}/items/{item_id}", headers=headers)
            if r.status_code == 200:
                log("测试数据清理成功")
            else:
                log(f"清理失败: {r.status_code}", False)
        except Exception as e:
            pass

if __name__ == "__main__":
    test_auth_flow()
