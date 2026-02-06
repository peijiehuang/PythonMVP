import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel, select
from sqlmodel.pool import StaticPool
import sys

# 导入应用实例
from main import app
from app.core.config import settings
from app.api.deps import get_session
from app.core.security import get_password_hash
from app.models.models import User, Item

# ==========================================
# 🧪 测试隔离：使用异步内存数据库
# ==========================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# 创建独立于生产环境的测试引擎
# 使用 StaticPool 确保在单连接中维持内存数据库状态
test_engine = create_async_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool,
)

# 测试专用的 Session 工厂
test_async_session_maker = async_sessionmaker(
    test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def create_test_data(session: AsyncSession):
    """注入测试所需的预设数据"""
    result = await session.execute(select(User).where(User.username == "admin"))
    user = result.scalars().first()
    if not user:
        hashed_pwd = get_password_hash("admin")
        admin_user = User(username="admin", hashed_password=hashed_pwd)
        session.add(admin_user)
        await session.commit()

# --- 核心：动态覆盖 FastAPI 依赖注入 ---
async def get_test_session():
    """让应用在测试期间使用我们的测试数据库"""
    async with test_async_session_maker() as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

# ==========================================
# 🛠️ Pytest 固件 (Fixtures)
# ==========================================

@pytest.fixture
async def client():
    """
    异步测试客户端固件
    流程：建表 -> 注入数据 -> 运行测试 -> 删表
    """
    # 1. 建立测试表结构
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 2. 注入初始账号
    async with test_async_session_maker() as session:
        await create_test_data(session)

    # 3. 初始化异步 HTTP 客户端
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    # 4. 清理环境 (删除内存数据库表)
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

# ==========================================
# 📑 自动化测试用例
# ==========================================

async def test_read_items_public(client: AsyncClient):
    """场景：未登录状态下允许读取列表"""
    response = await client.get(f"{settings.API_V1_STR}/items/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert isinstance(json_data["data"], list)

async def test_create_item_unauthorized(client: AsyncClient):
    """场景：未登录状态下禁止创建操作"""
    response = await client.post(f"{settings.API_V1_STR}/items/", json={"name": "黑客物品"})
    # 期望返回 401
    assert response.status_code == 401
    assert response.json()["success"] is False

async def test_login_success(client: AsyncClient):
    """场景：使用默认管理员账号登录"""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token", 
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

async def test_auth_flow_full_cycle(client: AsyncClient):
    """场景：完整的业务链路逻辑测试"""
    
    # 1. 登录并获取 Token
    login_res = await client.post(
        f"{settings.API_V1_STR}/auth/token", 
        data={"username": "admin", "password": "admin"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 并发创建测试
    item_data = {"name": "测试物品", "description": "由自动化测试创建"}
    create_res = await client.post(
        f"{settings.API_V1_STR}/items/", 
        json=item_data, 
        headers=headers
    )
    assert create_res.status_code == 200
    created_item = create_res.json()["data"]
    item_id = created_item["id"]

    # 3. 读取详情
    read_res = await client.get(f"{settings.API_V1_STR}/items/{item_id}")
    assert read_res.status_code == 200
    assert read_res.json()["data"]["name"] == "测试物品"

    # 4. 更新字段
    update_data = {"description": "描述已更新"}
    patch_res = await client.patch(
        f"{settings.API_V1_STR}/items/{item_id}", 
        json=update_data, 
        headers=headers
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["description"] == "描述已更新"

    # 5. 执行删除
    del_res = await client.delete(
        f"{settings.API_V1_STR}/items/{item_id}", 
        headers=headers
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
    
    # 6. 验证删除结果
    get_res = await client.get(f"{settings.API_V1_STR}/items/{item_id}")
    assert get_res.status_code == 404

async def test_login_failure(client: AsyncClient):
    """场景：输入错误密码时的异常处理"""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token", 
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["success"] is False
