import asyncio
import httpx
import time
import statistics
import sys
from main import app # 导入 FastAPI 实例

BASE_URL = "http://testserver/api/v1"

async def benchmark_endpoint(name, func, count, concurrency, client):
    print(f"正在测试 {name}: 总计 {count} 请求, 并发数 {concurrency}...")
    semaphore = asyncio.Semaphore(concurrency)
    latencies = []

    async def task():
        async with semaphore:
            start = time.perf_counter()
            await func(client)
            end = time.perf_counter()
            latencies.append(end - start)

    start_total = time.perf_counter()
    await asyncio.gather(*(task() for _ in range(count)))
    end_total = time.perf_counter()

    total_time = end_total - start_total
    rps = count / total_time
    avg = sum(latencies) / len(latencies)
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 0 else 0
    p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) > 0 else 0

    print(f"结果 [{name}]:")
    print(f"  总耗时:     {total_time:.2f}s")
    print(f"  RPS (吞吐量): {rps:.2f} req/s")
    print(f"  平均延迟:    {avg*1000:.2f}ms")
    print(f"  P95 延迟:    {p95*1000:.2f}ms")
    print(f"  P99 延迟:    {p99*1000:.2f}ms")
    print("-" * 40)
    return rps

async def main():
    # 使用 ASGITransport 直接测试 APP，排除真实网络环境抖动，直击内核性能
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL) as client:
        
        # 0. 准备工作：登录
        print("🔐 正在获取授权...")
        login_res = await client.post("/auth/token", data={"username": "admin", "password": "admin"})
        if login_res.status_code != 200:
            print("❌ 登录失败，请确保 admin 用户已初始化。")
            return
        token = login_res.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})

        item_ids = []

        # 1. 模拟并发创建
        async def create_op(c):
            r = await c.post("/items/", json={"name": "BenchItem", "description": "Performance Test"})
            if r.status_code == 200:
                item_ids.append(r.json()["id"])

        await benchmark_endpoint("并发创建 (CREATE)", create_op, 200, 20, client)

        # 2. 模拟并发查询 (列表)
        async def read_list_op(c):
            await c.get("/items/")

        await benchmark_endpoint("并发查询列表 (READ LIST)", read_list_op, 500, 50, client)

        # 3. 模拟并发修改
        if item_ids:
            target_id = item_ids[0] # 简化，修改同一个或循环修改
            async def update_op(c):
                await c.patch(f"/items/{target_id}", json={"name": "UpdatedBench"})

            await benchmark_endpoint("并发更新 (UPDATE)", update_op, 200, 20, client)

        # 4. 模拟并发删除
        # 我们需要足够多的 ID 来删除
        to_delete = item_ids.copy()
        async def delete_op(c):
            if to_delete:
                tid = to_delete.pop()
                await c.delete(f"/items/{tid}")

        await benchmark_endpoint("并发删除 (DELETE)", delete_op, len(item_ids), 20, client)

if __name__ == "__main__":
    # Windows 下异步策略兼容
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
