import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

# Updated Imports
from main import app
from core.database import get_session
from core.security import get_password_hash
from models.models import User

# ==========================================
# 1. 测试环境配置
# ==========================================

# 使用内存数据库进行测试隔离
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)

def create_test_data(session: Session):
    """创建测试所需的初始数据 (如 Admin 用户)"""
    user = session.exec(select(User).where(User.username == "admin")).first()
    if not user:
        hashed_pwd = get_password_hash("admin")
        admin_user = User(username="admin", hashed_password=hashed_pwd)
        session.add(admin_user)
        session.commit()

# 覆盖 get_session 依赖
def get_test_session():
    with Session(test_engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture(name="client")
def client_fixture():
    # 每个测试前重建数据库结构
    SQLModel.metadata.create_all(test_engine)
    
    # 注入初始数据
    with Session(test_engine) as session:
        create_test_data(session)

    client = TestClient(app)
    yield client
    
    # 清理数据库
    SQLModel.metadata.drop_all(test_engine)

# ==========================================
# 2. 测试用例
# ==========================================

def test_read_items_public(client: TestClient):
    """测试公开接口访问"""
    response = client.get("/items/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_item_unauthorized(client: TestClient):
    """测试未登录创建物品 (期望 401)"""
    response = client.post("/items/", json={"name": "Hacker Item"})
    assert response.status_code == 401

def test_login_success(client: TestClient):
    """测试登录获取 Token"""
    response = client.post("/token", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_auth_flow_full_cycle(client: TestClient):
    """完整业务流测试: 登录 -> 创建 -> 查询 -> 修改 -> 删除"""
    
    # 1. Login
    login_res = client.post("/token", data={"username": "admin", "password": "admin"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create
    item_data = {"name": "Test Item", "description": "For Pytest"}
    create_res = client.post("/items/", json=item_data, headers=headers)
    assert create_res.status_code == 200
    created_item = create_res.json()
    assert created_item["name"] == item_data["name"]
    item_id = created_item["id"]

    # 3. Read
    read_res = client.get(f"/items/{item_id}")
    assert read_res.status_code == 200
    assert read_res.json()["description"] == "For Pytest"

    # 4. Update
    update_data = {"description": "Updated Description"}
    patch_res = client.patch(f"/items/{item_id}", json=update_data, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["description"] == "Updated Description"

    # 5. Delete
    del_res = client.delete(f"/items/{item_id}", headers=headers)
    assert del_res.status_code == 200
    
    # Verify Deletion
    get_res = client.get(f"/items/{item_id}")
    assert get_res.status_code == 404

def test_login_failure(client: TestClient):
    """测试错误密码"""
    response = client.post("/token", data={"username": "admin", "password": "wrongpassword"})
    # main.py logic changed: raise HTTPException(status_code=400, ...)
    # Wait, in the code snippet I wrote 400. Let me check what I wrote in main.py.
    # In main.py: raise HTTPException(status_code=400...)
    # But usually 401 is for auth failure.
    # Let's fix test expectation to 400 or fix main.py to 401. 
    # OAuth2 spec says 400 for invalid_grant, but FastAPI default is usually 401 for simplicity.
    # I wrote 400 in main.py explicitly. So I should assert 400 here.
    assert response.status_code == 400