import json
import random
import asyncio
import httpx
import time

VLLM_URL = "http://localhost:11434"
TEACHER_MODEL = "/datadisk/home/lsr/qwen2.5-72b-awq"
OUTPUT_PATH = "finetune_data_2000.json"

CONCURRENCY_LIMIT = 40  # 8张卡并发40毫无压力
TOTAL_SAMPLES = 2000

# --- 因子池：用于裂变组合 ---
TRENDS = ["低位横盘后首板涨停", "高位放量滞涨收长上影", "连续三日缩量阴跌", "沿5日线稳步攀升", "跳空低开破位下杀", "探底回升收单针探底"]
VOLUMES = ["缩量至近期地量", "温和放量", "爆出历史天量", "量比大于3.0", "缩量涨停被砸"]
EVENTS = [
    "大基金宣布减持", "获机构密集调研", "所属概念迎国家级政策利好", "美国商务部更新实体清单",
    "业绩预告同比大增100%", "核心高管离职", "中标亿元政务大单", "无明显消息刺激（纯资金博弈）"
]
INDICATORS = ["RSI底背离", "MACD高位死叉", "KDJ即将金叉", "布林带走平", "偏离均线过远(超买)"]

STOCKS = [
    ("002230", "科大讯飞", "AI应用"), ("688256", "寒武纪", "AI芯片"),
    ("603019", "中科曙光", "AI算力"), ("300474", "景嘉微", "AI芯片"),
    ("688111", "金山办公", "AI应用"), ("300496", "中科创达", "端侧AI"),
    ("688561", "奇安信", "AI安全"), ("688047", "龙芯中科", "信创芯片"),
    ("300308", "中际旭创", "CPO光模块"), ("002415", "海康威视", "AI视觉")
]

TEACHER_SYSTEM = (
    "你是一位常年霸榜新财富的顶级券商TMT首席分析师。请对给定的盘面组合进行极度深度的推演。\n"
    "【核心要求】：\n"
    "1. 拒绝表面看图说话，必须揭示主力资金意图（如：试盘、洗盘、诱多、出货）。\n"
    "2. 必须结合给定的消息面，分析它是被提前兑现了，还是情绪刚刚发酵。\n"
    "3. 结论要求极其果断（如：坚决斩仓、逢低加仓、持股观望），禁止模棱两可。\n"
    "输出格式：直接输出研报正文，不要Markdown，分段清晰。"
)

stats = {"done": 0, "failed": 0}

async def fetch_data(client, prompt, sem):
    async with sem:
        try:
            resp = await client.post(
                f"{VLLM_URL}/v1/chat/completions",
                json={
                    "model": TEACHER_MODEL,
                    "messages": [{"role": "system", "content": TEACHER_SYSTEM}, {"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.85 
                },
                timeout=240.0
            )
            if resp.status_code == 200:
                stats["done"] += 1
                if stats["done"] % 20 == 0:
                    print(f"🚀 [进度播报] 已成功生成: {stats['done']}/{TOTAL_SAMPLES} 条...")
                return prompt, resp.json()["choices"][0]["message"]["content"]
            else:
                stats["failed"] += 1
                return prompt, None
        except Exception as e:
            stats["failed"] += 1
            return prompt, None

async def main():
    print(f"⚡ 开始启动高并发数据蒸馏 | 并发量: {CONCURRENCY_LIMIT}")
    start_time = time.time()
    
    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
    dataset = []
    prompts = []
    
    for _ in range(TOTAL_SAMPLES):
        stock = random.choice(STOCKS)
        p = (f"目标标的：{stock[1]}({stock[0]})，所属板块：{stock[2]}。\n"
             f"今日盘面特征：{random.choice(TRENDS)}，且{random.choice(VOLUMES)}。\n"
             f"技术形态：{random.choice(INDICATORS)}。\n"
             f"消息面驱动：{random.choice(EVENTS)}。\n"
             f"请给出深度盘面解析与明日操作策略。")
        prompts.append(p)
        
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(fetch_data(client, p, sem)) for p in prompts]
        
        for coro in asyncio.as_completed(tasks):
            prompt, answer = await coro
            if answer and len(answer) > 100:
                dataset.append({
                    "messages": [
                        {"role": "system", "content": "你是专业A股AI产业链分析师。输出要求纯文本、去套话、结论果断。"},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer}
                    ]
                })
                
                # 每 100 条安全落盘一次
                if len(dataset) % 100 == 0:
                    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                        json.dump(dataset, f, ensure_ascii=False, indent=2)
                    print(f"💾 已安全落盘 {len(dataset)} 条数据...")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
        
    cost_time = (time.time() - start_time) / 60
    print(f"✅ 大功告成！耗时 {cost_time:.2f} 分钟。共收集 {len(dataset)} 条高质量数据。失败 {stats['failed']} 条。")

if __name__ == "__main__":
    asyncio.run(main())
