import json
import random
import time
import requests
import os

VLLM_URL = "http://localhost:11434"
TEACHER_MODEL = "/datadisk/home/lsr/qwen2.5-72b-awq"
OUTPUT_PATH = "finetune_data_2000.json"

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

def call_teacher(prompt):
    try:
        resp = requests.post(f"{VLLM_URL}/v1/chat/completions", json={
            "model": TEACHER_MODEL,
            "messages": [{"role": "system", "content": TEACHER_SYSTEM}, {"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.85 
        }, timeout=120)
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API Error: {e}")
        return None

def main():
    print("🚀 开始执行 2000 条海量动态因子蒸馏...")
    dataset = []
    total_samples = 2000 
    
    for i in range(total_samples):
        stock = random.choice(STOCKS)
        
        # 动态组合因子，产生化学反应
        prompt = (f"目标标的：{stock[1]}({stock[0]})，所属板块：{stock[2]}。\n"
                  f"今日盘面特征：{random.choice(TRENDS)}，且{random.choice(VOLUMES)}。\n"
                  f"技术形态：{random.choice(INDICATORS)}。\n"
                  f"消息面驱动：{random.choice(EVENTS)}。\n"
                  f"请给出深度盘面解析与明日操作策略。")
        
        if i % 10 == 0:
            print(f"⏳ 进度: [{i}/{total_samples}] 正在蒸馏...")
            
        answer = call_teacher(prompt)
        
        if answer and len(answer) > 100:
            dataset.append({
                "messages": [
                    {"role": "system", "content": "你是专业A股AI产业链分析师。输出要求纯文本、去套话、结论果断。"},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": answer}
                ]
            })
        
        # 每 100 条实时落盘一次，防止意外中断丢失数据
        if (i + 1) % 100 == 0:
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            print(f"💾 已安全落盘 {len(dataset)} 条数据...")
            
    print(f"✅ 蒸馏大功告成！共计生成 {len(dataset)} 条高质量数据。")

if __name__ == "__main__":
    main()
