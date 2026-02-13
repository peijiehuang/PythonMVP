"""
代码生成器 API
根据数据库表结构自动生成 CRUD 后端接口、Schema、前端页面代码。
"""
import os
import re
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import SQLModel

from app.api.deps import CurrentUser
from app.schemas.responses import resp_ok

router = APIRouter()

# --- 系统表黑名单，不参与代码生成 ---
SYSTEM_TABLES = {"user", "tasklog", "taskconfig"}


# --- 请求模型 ---

class PreviewRequest(BaseModel):
    table_name: str

class DownloadRequest(BaseModel):
    table_name: str
    file_type: str  # endpoint | schema | frontend

class SaveRequest(BaseModel):
    table_name: str


# --- 工具函数 ---

def _pluralize(name: str) -> str:
    """简易英文复数（满足常见场景）"""
    if name.endswith("s"):
        return name + "es"
    if name.endswith("y") and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


def _sql_type_to_python(col) -> str:
    """SQLAlchemy 列类型 → Python 类型字符串"""
    type_name = type(col.type).__name__.upper()
    mapping = {
        "INTEGER": "int",
        "BIGINTEGER": "int",
        "SMALLINTEGER": "int",
        "FLOAT": "float",
        "DOUBLE": "float",
        "NUMERIC": "float",
        "DECIMAL": "float",
        "VARCHAR": "str",
        "TEXT": "str",
        "STRING": "str",
        "BOOLEAN": "bool",
        "DATETIME": "datetime",
        "DATE": "date",
        "TIME": "time",
    }
    return mapping.get(type_name, "str")


def _get_table_info(table_name: str):
    """获取表的元数据：类名、列信息"""
    table_name_lower = table_name.lower()
    table_obj = SQLModel.metadata.tables.get(table_name_lower)
    if table_obj is None:
        raise HTTPException(status_code=404, detail=f"表 '{table_name}' 不存在")

    # 通过 SQLModel 子类反查类名
    class_name = table_name.capitalize()
    for cls in SQLModel.__subclasses__():
        if hasattr(cls, "__tablename__") and cls.__tablename__ == table_name_lower:
            class_name = cls.__name__
            break
        if hasattr(cls, "metadata") and cls.__name__.lower() == table_name_lower:
            class_name = cls.__name__
            break

    columns = []
    for col in table_obj.columns:
        columns.append({
            "name": col.name,
            "type": _sql_type_to_python(col),
            "primary_key": col.primary_key,
            "nullable": col.nullable,
            "has_default": col.default is not None or col.server_default is not None,
        })
    return class_name, columns


def _get_all_tables():
    """列出所有非系统表"""
    tables = []
    for tname, tobj in SQLModel.metadata.tables.items():
        if tname.lower() in SYSTEM_TABLES:
            continue
        class_name = tname.capitalize()
        for cls in SQLModel.__subclasses__():
            if hasattr(cls, "__tablename__") and cls.__tablename__ == tname:
                class_name = cls.__name__
                break
            if cls.__name__.lower() == tname:
                class_name = cls.__name__
                break

        cols = []
        for col in tobj.columns:
            cols.append({
                "name": col.name,
                "type": _sql_type_to_python(col),
                "primary_key": col.primary_key,
                "nullable": col.nullable,
                "has_default": col.default is not None or col.server_default is not None,
            })
        tables.append({"table_name": tname, "class_name": class_name, "columns": cols})
    return tables


# --- 代码生成函数 ---

def _generate_endpoint_code(class_name: str, table_name: str, columns: list) -> str:
    """生成 Endpoint 代码（复刻 items.py 模式）"""
    plural = _pluralize(table_name)
    var = table_name.lower()

    # 筛选出业务字段（排除 id、created_at、updated_at）
    auto_fields = {"id", "created_at", "updated_at"}
    biz_cols = [c for c in columns if c["name"] not in auto_fields]

    # 搜索用的第一个 str 字段
    search_field = None
    for c in biz_cols:
        if c["type"] == "str" and not c["primary_key"]:
            search_field = c["name"]
            break

    search_block = ""
    if search_field:
        search_block = f"""
    if keyword:
        query = query.where(col({class_name}.{search_field}).contains(keyword))"""

    # 排序字段
    has_created_at = any(c["name"] == "created_at" for c in columns)
    order_field = f"{class_name}.created_at.desc()" if has_created_at else f"{class_name}.id.desc()"

    code = f'''from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from sqlmodel import select, col

from app.api.deps import SessionDep, CurrentUser
from app.models.models import {class_name}
from app.schemas.schemas_{plural} import {class_name}Create, {class_name}Update, {class_name}Read
from app.schemas.responses import resp_ok

router = APIRouter()


@router.post("/", response_model=None)
async def create_{var}(
    {var}_in: {class_name}Create,
    session: SessionDep,
    current_user: CurrentUser
):
    """创建{class_name}"""
    db_{var} = {class_name}.model_validate({var}_in)
    session.add(db_{var})
    await session.commit()
    await session.refresh(db_{var})
    return resp_ok(data=db_{var})


@router.get("/", response_model=None)
async def read_{plural}(
    session: SessionDep,
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """分页获取{class_name}列表"""
    query = select({class_name}){search_block}
    query = query.order_by({order_field})
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    return resp_ok(data=result.scalars().all())


@router.get("/{{item_id}}", response_model=None)
async def read_{var}(item_id: int, session: SessionDep):
    """获取单个{class_name}详情"""
    {var} = await session.get({class_name}, item_id)
    if not {var}:
        raise HTTPException(status_code=404, detail="{class_name}不存在")
    return resp_ok(data={var})


@router.patch("/{{item_id}}", response_model=None)
async def update_{var}(
    item_id: int,
    {var}_in: {class_name}Update,
    session: SessionDep,
    current_user: CurrentUser
):
    """部分更新{class_name}"""
    db_{var} = await session.get({class_name}, item_id)
    if not db_{var}:
        raise HTTPException(status_code=404, detail="{class_name}不存在")

    input_data = {var}_in.model_dump(exclude_unset=True)
    for key, value in input_data.items():
        setattr(db_{var}, key, value)
'''
    if has_created_at:
        code += f"    db_{var}.updated_at = datetime.now(timezone.utc)\n"

    code += f'''
    session.add(db_{var})
    await session.commit()
    await session.refresh(db_{var})
    return resp_ok(data=db_{var})


@router.delete("/{{item_id}}")
async def delete_{var}(
    item_id: int,
    session: SessionDep,
    current_user: CurrentUser
):
    """删除{class_name}"""
    {var} = await session.get({class_name}, item_id)
    if not {var}:
        raise HTTPException(status_code=404, detail="{class_name}不存在")
    await session.delete({var})
    await session.commit()
    return resp_ok(message="{class_name}删除成功")
'''
    return code


def _generate_schema_code(class_name: str, table_name: str, columns: list) -> str:
    """生成 Schema 代码（复刻 schemas.py 模式）"""
    auto_fields = {"id", "created_at", "updated_at"}
    biz_cols = [c for c in columns if c["name"] not in auto_fields]

    # 判断是否需要 datetime 导入
    needs_datetime = any(c["name"] in ("created_at", "updated_at") for c in columns)
    datetime_import = "\nfrom datetime import datetime" if needs_datetime else ""

    # Create schema 字段
    create_fields = []
    for c in biz_cols:
        py_type = c["type"]
        if c["nullable"] or c["has_default"]:
            create_fields.append(f"    {c['name']}: Optional[{py_type}] = None")
        else:
            create_fields.append(f"    {c['name']}: {py_type}")

    # Update schema 字段（全部 Optional）
    update_fields = []
    for c in biz_cols:
        py_type = c["type"]
        update_fields.append(f"    {c['name']}: Optional[{py_type}] = None")

    # Read schema 字段
    read_fields = ["    id: int"]
    for c in biz_cols:
        py_type = c["type"]
        if c["nullable"]:
            read_fields.append(f"    {c['name']}: Optional[{py_type}] = None")
        else:
            read_fields.append(f"    {c['name']}: {py_type}")
    if needs_datetime:
        read_fields.append("    created_at: datetime")
        read_fields.append("    updated_at: datetime")

    code = f'''from pydantic import BaseModel
from typing import Optional{datetime_import}


class {class_name}Create(BaseModel):
    """创建{class_name}时的输入"""
{chr(10).join(create_fields) if create_fields else "    pass"}


class {class_name}Update(BaseModel):
    """更新{class_name}时的输入（全部可选）"""
{chr(10).join(update_fields) if update_fields else "    pass"}


class {class_name}Read(BaseModel):
    """读取{class_name}时的输出"""
{chr(10).join(read_fields)}
'''
    return code


def _generate_frontend_code(class_name: str, table_name: str, columns: list) -> str:
    """生成前端页面代码（复刻 index.html 模式）"""
    plural = _pluralize(table_name)
    var = table_name.lower()

    auto_fields = {"id", "created_at", "updated_at"}
    biz_cols = [c for c in columns if c["name"] not in auto_fields]

    # 搜索字段
    search_field = None
    for c in biz_cols:
        if c["type"] == "str":
            search_field = c["name"]
            break

    # Vue formItem 初始化
    form_init_parts = ["id: null"]
    for c in biz_cols:
        if c["type"] == "bool":
            form_init_parts.append(f"{c['name']}: true")
        else:
            form_init_parts.append(f"{c['name']}: ''")
    form_init = ", ".join(form_init_parts)

    # formItem 重置
    form_reset_parts = ["formItem.id = null;"]
    for c in biz_cols:
        if c["type"] == "bool":
            form_reset_parts.append(f"                        formItem.{c['name']} = true;")
        else:
            form_reset_parts.append(f"                        formItem.{c['name']} = '';")
    form_reset = "\n".join(form_reset_parts)

    # 表单输入字段
    form_inputs = []
    for c in biz_cols:
        label = c["name"].replace("_", " ").title()
        if c["type"] == "bool":
            form_inputs.append(f"""                    <div class="form-control">
                         <label class="label cursor-pointer justify-between border border-slate-200 rounded-xl px-4 py-3">
                            <span class="label-text font-bold text-slate-700">{label}</span>
                            <input type="checkbox" v-model="formItem.{c['name']}" class="toggle toggle-success toggle-sm" />
                        </label>
                    </div>""")
        elif c["nullable"]:
            form_inputs.append(f"""                    <div class="form-control w-full">
                        <label class="label pt-0"><span class="label-text text-xs font-bold text-slate-500 uppercase">{label}</span></label>
                        <textarea v-model="formItem.{c['name']}" class="textarea textarea-bordered h-24 rounded-xl"></textarea>
                    </div>""")
        else:
            input_type = "number" if c["type"] in ("int", "float") else "text"
            form_inputs.append(f"""                    <div class="form-control w-full">
                        <label class="label pt-0"><span class="label-text text-xs font-bold text-slate-500 uppercase">{label}</span></label>
                        <input type="{input_type}" v-model="formItem.{c['name']}" class="input input-bordered w-full rounded-xl" />
                    </div>""")
    form_inputs_html = "\n".join(form_inputs)

    # 列表展示的主字段
    display_name = biz_cols[0]["name"] if biz_cols else "id"
    display_desc = biz_cols[1]["name"] if len(biz_cols) > 1 else None

    desc_line = ""
    if display_desc:
        desc_line = f"""
                        <p class="text-sm text-slate-500 font-normal mt-0.5 line-clamp-1 max-w-md">
                            {{{{ item.{display_desc} || 'No description.' }}}}
                        </p>"""

    has_updated_at = any(c["name"] == "updated_at" for c in columns)
    time_col = ""
    if has_updated_at:
        time_col = """
                    <div class="text-right hidden sm:block">
                        <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Updated</div>
                        <div class="text-sm font-medium text-slate-600">{{ formatTime(item.updated_at) }}</div>
                    </div>"""

    has_active = any(c["name"] == "is_active" for c in biz_cols)
    if has_active:
        icon_block = """
                    <div class="w-12 h-12 rounded-2xl flex items-center justify-center"
                        :class="item.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'">
                        <svg v-if="item.is_active" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                        </svg>
                    </div>"""
    else:
        icon_block = """
                    <div class="w-12 h-12 rounded-2xl flex items-center justify-center bg-primary/10 text-primary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                        </svg>
                    </div>"""

    search_html = ""
    if search_field:
        search_html = f"""
                <div class="relative group w-full md:w-64">
                    <input type="text" v-model="keyword" @keyup.enter="fetchItems" placeholder="Type to search..."
                        class="input input-bordered w-full bg-white/80 backdrop-blur border-slate-200 focus:border-primary focus:ring-4 focus:ring-primary/10 rounded-xl pl-10 transition-all" />
                    <span class="absolute left-3.5 top-3 text-slate-400 group-focus-within:text-primary transition-colors">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </span>
                </div>"""

    code = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{class_name} Management</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.6.0/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{ sans: ['Inter', 'sans-serif'] }},
                    colors: {{ primary: '#4F46E5', surface: '#ffffff' }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #F8FAFC; }}
        .card-hover {{ transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }}
        .card-hover:hover {{ transform: translateY(-2px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); }}
    </style>
</head>
<body class="text-slate-800 min-h-screen">
<div id="app" class="max-w-5xl mx-auto py-12 px-6">

    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-end mb-10 gap-6">
        <div>
            <div class="text-xs font-bold text-primary tracking-widest uppercase mb-2">Workspace</div>
            <h1 class="text-4xl font-extrabold text-slate-900 tracking-tight">
                {class_name} <span class="text-slate-300">/</span> Management
            </h1>
            <p class="text-slate-500 mt-2 font-light">
                <span v-if="user" class="text-emerald-600 font-medium">Hello, {{{{ user.username }}}}!</span>
            </p>
        </div>
        <div class="flex gap-3 w-full md:w-auto items-center">
            <a href="/" class="btn btn-ghost btn-circle btn-sm text-slate-400 hover:text-primary" title="返回首页">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0h4" />
                </svg>
            </a>
            <div v-if="!user">
                <button @click="openLoginModal" class="btn btn-ghost btn-sm text-slate-500 hover:text-primary">Login</button>
            </div>
            <div v-else class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn btn-ghost btn-circle avatar placeholder">
                    <div class="bg-primary text-white rounded-full w-10">
                        <span class="text-xs">{{{{ user.username.substring(0,2).toUpperCase() }}}}</span>
                    </div>
                </div>
                <ul tabindex="0" class="mt-3 z-[1] p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-52">
                    <li><a @click="logout" class="text-red-500">Logout</a></li>
                </ul>
            </div>{search_html}
            <button class="btn btn-primary border-none bg-primary hover:bg-indigo-700 text-white shadow-lg shadow-primary/30 rounded-xl px-6"
                @click="checkAuthAndOpenModal()">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                New {class_name}
            </button>
        </div>
    </div>

    <!-- List -->
    <div class="space-y-4">
        <div v-if="loading" class="flex flex-col items-center justify-center py-20 space-y-4">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        <div v-else v-for="item in items" :key="item.id"
            class="card-hover bg-white/70 backdrop-blur-sm border border-white/50 p-5 rounded-2xl flex items-center justify-between group">
            <div class="flex items-center gap-6">{icon_block}
                <div>
                    <h3 class="font-bold text-lg text-slate-800">{{{{ item.{display_name} }}}}</h3>{desc_line}
                </div>
            </div>
            <div class="flex items-center gap-8">{time_col}
                <div class="flex gap-2">
                    <button class="btn btn-circle btn-sm btn-ghost text-slate-400 hover:bg-primary/10 hover:text-primary" @click="checkAuthAndOpenModal(item)">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                    </button>
                    <button class="btn btn-circle btn-sm btn-ghost text-slate-400 hover:bg-red-50 hover:text-red-500" @click="deleteItem(item.id)">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
        <div v-if="!loading && items.length === 0" class="border-2 border-dashed border-slate-200 rounded-3xl p-12 text-center bg-slate-50/50">
            <h3 class="text-lg font-bold text-slate-700">No {class_name} yet</h3>
            <p class="text-slate-500 text-sm mt-1 mb-6">Create your first {var} to get started.</p>
            <button class="btn btn-outline btn-primary btn-sm rounded-lg" @click="checkAuthAndOpenModal()">Create Now</button>
        </div>
    </div>

    <!-- Edit Modal -->
    <dialog ref="item_modal" class="modal backdrop-blur-sm">
        <div class="modal-box bg-white p-8 rounded-3xl shadow-2xl border border-slate-100 max-w-md">
            <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button></form>
            <h3 class="font-bold text-xl text-slate-900 mb-6">{{{{ formItem.id ? 'Edit {class_name}' : 'New {class_name}' }}}}</h3>
            <div class="space-y-5">
{form_inputs_html}
            </div>
            <div class="modal-action mt-8">
                <button class="btn btn-primary w-full rounded-xl" @click="submitForm" :disabled="submitting">
                    {{{{ submitting ? 'Saving...' : 'Save Changes' }}}}
                </button>
            </div>
        </div>
    </dialog>

    <!-- Login Modal -->
    <dialog ref="login_modal" class="modal backdrop-blur-sm">
        <div class="modal-box bg-white p-8 rounded-3xl shadow-2xl border border-slate-100 max-w-sm">
            <form method="dialog"><button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">✕</button></form>
            <div class="text-center mb-6">
                <h3 class="font-bold text-2xl text-slate-900">Welcome Back</h3>
                <p class="text-slate-500 text-sm mt-1">Please sign in to continue.</p>
            </div>
            <div class="space-y-4">
                <div class="form-control w-full">
                    <input type="text" v-model="loginForm.username" placeholder="Username" class="input input-bordered w-full rounded-xl" @keyup.enter="handleLogin"/>
                </div>
                <div class="form-control w-full">
                    <input type="password" v-model="loginForm.password" placeholder="Password" class="input input-bordered w-full rounded-xl" @keyup.enter="handleLogin"/>
                </div>
                <div v-if="loginError" class="text-red-500 text-xs text-center">{{{{ loginError }}}}</div>
            </div>
            <div class="modal-action mt-6">
                <button class="btn btn-primary w-full rounded-xl" @click="handleLogin" :disabled="submitting">
                    {{{{ submitting ? 'Signing In...' : 'Sign In' }}}}
                </button>
            </div>
        </div>
    </dialog>
</div>

<script>
    const {{ createApp, ref, reactive, onMounted }} = Vue;
    createApp({{
        setup() {{
            const API_URL = '/api/v1/{plural}/';
            const items = ref([]);
            const keyword = ref("");
            const loading = ref(false);
            const submitting = ref(false);
            const user = ref(null);
            const loginForm = reactive({{ username: '', password: '' }});
            const loginError = ref('');
            const item_modal = ref(null);
            const login_modal = ref(null);
            const formItem = reactive({{ {form_init} }});

            const api = axios.create();
            api.interceptors.request.use(config => {{
                const token = localStorage.getItem('token');
                if (token) config.headers.Authorization = `Bearer ${{token}}`;
                return config;
            }});
            api.interceptors.response.use(r => r, error => {{
                if (error.response && error.response.status === 401) {{ logout(); openLoginModal(); }}
                return Promise.reject(error);
            }});

            const initAuth = async () => {{
                const token = localStorage.getItem('token');
                const username = localStorage.getItem('username');
                if (token && username) {{
                    try {{
                        await api.get('/api/v1/auth/me');
                        user.value = {{ username }};
                    }} catch (e) {{
                        localStorage.removeItem('token');
                        localStorage.removeItem('username');
                    }}
                }}
            }};
            const openLoginModal = () => {{ loginError.value = ''; loginForm.username = ''; loginForm.password = ''; login_modal.value.showModal(); }};
            const handleLogin = async () => {{
                if (!loginForm.username || !loginForm.password) return;
                submitting.value = true; loginError.value = '';
                try {{
                    const formData = new FormData();
                    formData.append('username', loginForm.username);
                    formData.append('password', loginForm.password);
                    const res = await axios.post('/api/v1/auth/token', formData);
                    localStorage.setItem('token', res.data.access_token);
                    localStorage.setItem('username', loginForm.username);
                    user.value = {{ username: loginForm.username }};
                    login_modal.value.close();
                    fetchItems();
                }} catch (e) {{ loginError.value = "Login failed."; }}
                finally {{ submitting.value = false; }}
            }};
            const logout = () => {{ localStorage.removeItem('token'); localStorage.removeItem('username'); user.value = null; }};

            const checkAuthAndOpenModal = (item = null) => {{
                if (!user.value) {{ openLoginModal(); return; }}
                if (item) Object.assign(formItem, item);
                else {{
                    {form_reset}
                }}
                item_modal.value.showModal();
            }};

            const fetchItems = async () => {{
                loading.value = true;
                try {{
                    const params = keyword.value ? {{ keyword: keyword.value }} : {{}};
                    const res = await api.get(API_URL, {{ params }});
                    items.value = res.data.data;
                }} catch (e) {{ console.error(e); }}
                finally {{ loading.value = false; }}
            }};

            const submitForm = async () => {{
                submitting.value = true;
                try {{
                    if (formItem.id) await api.patch(API_URL + formItem.id, formItem);
                    else {{
                        const {{ id, ...payload }} = formItem;
                        await api.post(API_URL, payload);
                    }}
                    item_modal.value.close();
                    fetchItems();
                }} catch (e) {{ alert("Operation failed. " + (e.response?.data?.message || e.message)); }}
                finally {{ submitting.value = false; }}
            }};

            const deleteItem = async (id) => {{
                if (!user.value) {{ openLoginModal(); return; }}
                if (!confirm("Are you sure?")) return;
                try {{ await api.delete(API_URL + id); fetchItems(); }} catch (e) {{ alert("Delete failed."); }}
            }};

            const formatTime = (iso) => {{
                if (!iso) return '';
                return new Date(iso).toLocaleDateString('en-US', {{ month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }});
            }};

            onMounted(async () => {{ await initAuth(); fetchItems(); }});

            return {{
                items, keyword, loading, submitting, formItem, item_modal, login_modal,
                user, loginForm, loginError,
                fetchItems, checkAuthAndOpenModal, submitForm, deleteItem, formatTime,
                openLoginModal, handleLogin, logout
            }};
        }}
    }}).mount('#app');
</script>
</body>
</html>'''
    return code


# --- 路由 ---

@router.get("/tables")
async def list_tables(user: CurrentUser):
    """列出所有可用业务表"""
    tables = _get_all_tables()
    return resp_ok(data=tables)


@router.post("/preview")
async def preview_code(req: PreviewRequest, user: CurrentUser):
    """生成代码预览"""
    class_name, columns = _get_table_info(req.table_name)
    plural = _pluralize(req.table_name.lower())

    endpoint_code = _generate_endpoint_code(class_name, req.table_name.lower(), columns)
    schema_code = _generate_schema_code(class_name, req.table_name.lower(), columns)
    frontend_code = _generate_frontend_code(class_name, req.table_name.lower(), columns)

    return resp_ok(data={
        "endpoint": {
            "filename": f"{plural}.py",
            "path": f"app/api/endpoints/{plural}.py",
            "code": endpoint_code,
        },
        "schema": {
            "filename": f"schemas_{plural}.py",
            "path": f"app/schemas/schemas_{plural}.py",
            "code": schema_code,
        },
        "frontend": {
            "filename": f"{plural}.html",
            "path": f"static/{plural}.html",
            "code": frontend_code,
        },
    })


@router.post("/download")
async def download_code(req: DownloadRequest, user: CurrentUser):
    """下载单个生成的代码文件"""
    class_name, columns = _get_table_info(req.table_name)
    plural = _pluralize(req.table_name.lower())

    generators = {
        "endpoint": (lambda: _generate_endpoint_code(class_name, req.table_name.lower(), columns), f"{plural}.py"),
        "schema": (lambda: _generate_schema_code(class_name, req.table_name.lower(), columns), f"schemas_{plural}.py"),
        "frontend": (lambda: _generate_frontend_code(class_name, req.table_name.lower(), columns), f"{plural}.html"),
    }

    if req.file_type not in generators:
        raise HTTPException(status_code=400, detail="file_type 必须是 endpoint/schema/frontend")

    gen_func, filename = generators[req.file_type]
    code = gen_func()

    buffer = BytesIO(code.encode("utf-8"))
    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/save")
async def save_to_project(req: SaveRequest, user: CurrentUser):
    """保存生成的代码到项目目录"""
    class_name, columns = _get_table_info(req.table_name)
    table_lower = req.table_name.lower()
    plural = _pluralize(table_lower)

    endpoint_path = f"app/api/endpoints/{plural}.py"
    schema_path = f"app/schemas/schemas_{plural}.py"
    frontend_path = f"static/{plural}.html"

    # 检查文件是否已存在
    existing = []
    for p in [endpoint_path, schema_path, frontend_path]:
        if os.path.exists(p):
            existing.append(p)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"以下文件已存在，拒绝覆盖: {', '.join(existing)}"
        )

    # 生成代码
    endpoint_code = _generate_endpoint_code(class_name, table_lower, columns)
    schema_code = _generate_schema_code(class_name, table_lower, columns)
    frontend_code = _generate_frontend_code(class_name, table_lower, columns)

    written_files = []

    # 写入文件
    with open(endpoint_path, "w", encoding="utf-8") as f:
        f.write(endpoint_code)
    written_files.append(endpoint_path)

    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_code)
    written_files.append(schema_path)

    with open(frontend_path, "w", encoding="utf-8") as f:
        f.write(frontend_code)
    written_files.append(frontend_path)

    # 自动追加路由到 api.py
    api_py_path = "app/api/api.py"
    api_content = open(api_py_path, "r", encoding="utf-8").read()
    import_line = f"from app.api.endpoints import {plural}"
    include_line = f'api_router.include_router({plural}.router, prefix="/{plural}", tags=["{plural}"])'

    if plural not in api_content:
        # 在最后一个 import 行后追加
        lines = api_content.rstrip().split("\n")
        # 找到最后一个 from app.api.endpoints import 行
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("from app.api.endpoints"):
                last_import_idx = i
        lines.insert(last_import_idx + 1, import_line)
        lines.append(include_line)
        with open(api_py_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        written_files.append(f"{api_py_path} (已追加路由)")

    # 自动追加页面路由到 main.py
    main_py_path = "main.py"
    main_content = open(main_py_path, "r", encoding="utf-8").read()
    page_route = f'''
@app.get("/{plural}")
async def get_{plural}_page():
    """{class_name}管理页面"""
    return FileResponse("static/{plural}.html")
'''
    if f'"/{plural}"' not in main_content and f"'/{plural}'" not in main_content:
        # 在 read_index 函数之前插入
        insert_marker = '@app.get("/")'
        if insert_marker in main_content:
            main_content = main_content.replace(insert_marker, page_route + "\n" + insert_marker)
            with open(main_py_path, "w", encoding="utf-8") as f:
                f.write(main_content)
            written_files.append(f"{main_py_path} (已追加页面路由)")

    return resp_ok(
        data={"written_files": written_files},
        message=f"代码已保存！共写入 {len(written_files)} 个文件。重启服务后即可访问 /{plural} 页面。"
    )
