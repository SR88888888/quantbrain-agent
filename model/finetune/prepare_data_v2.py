import json
import random
import time
import requests

VLLM_URL = "http://localhost:11434"
TEACHER_MODEL = "/datadisk/home/lsr/qwen2.5-72b-awq"
OUTPUT_PATH = "finetune_data_v2.json"

# 极度扩充场景池，确保 500 条数据不重样
COMPLEX_SCENARIOS = [
    "突发利好但技术面处于高位超买，资金出现分歧",
    "业绩超预期但股价不涨反跌，疑似利好出尽",
    "板块集体回调，但个股缩量横盘表现极其抗跌",
    "主力资金持续流出，但技术指标RSI出现底背离",
    "产业政策发布，但受限于外部出口管制升级，市场观望浓厚",
    "放量突破关键压力位，且所属产业链上下游协同走强",
    "处于超卖区域后的首个放量涨停，分析反转可靠性",
    "机构调研记录显示产能利用率超负荷，但二级市场反应平淡",
    "大宗交易频繁出现折价成交，分析对短期股价的压制",
    "传导逻辑：上游算力芯片涨价对下游AI应用端利润的挤压分析"
]

STOCKS = [
    ("002230", "科大讯飞", "AI应用"), ("688256", "寒武纪", "AI芯片"),
    ("603019", "中科曙光", "AI算力"), ("300474", "景嘉微", "AI芯片"),
    ("688111", "金山办公", "AI应用"), ("300496", "中科创达", "端侧AI"),
    ("688561", "奇安信", "AI安全"), ("688047", "龙芯中科", "信创芯片")
]

TEACHER_SYSTEM = (
    "你是顶级券商TMT首席分析师。请对给定的个股数据进行深度复盘。\n"
    "分析要求：\n"
    "1. [深度逻辑] 必须包含量价、基本面和市场心理的推演。\n"
    "2. [专业术语] 熟练使用支撑位、背离、洗盘、获利回吐等词汇。\n"
    "3. [结论果断] 不允许出现‘可能’、‘大概’，必须给出明确方向。\n"
    "格式：先给出【逻辑推演】，最后给出【研报结论】。禁止Markdown符号。"
)

def call_teacher(prompt):
    try:
        resp = requests.post(f"{VLLM_URL}/v1/chat/completions", json={
            "model": TEACHER_MODEL,
            "messages": [{"role": "system", "content": TEACHER_SYSTEM}, {"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.85 # 调高多样性
        }, timeout=120)
        return resp.json()["choices"][0]["message"]["content"]
    except: return None

def main():
    print("开始生成 500 条深度蒸馏数据...")
    dataset = []
    total_samples = 500 
    
    for i in range(total_samples):
        stock = random.choice(STOCKS)
        scenario = random.choice(COMPLEX_SCENARIOS)
        price = round(random.uniform(30, 450), 2)
        chg = round(random.uniform(-10, 10), 2)
        vol_ratio = round(random.uniform(0.3, 5.0), 1)
        rsi = random.randint(10, 90)
        
        user_input = (f"分析 {stock[1]}({stock[0]})，{stock[2]}板块。\n"
                      f"即时数据：现价{price}，涨跌{chg}%，量比{vol_ratio}，RSI={rsi}。\n"
                      f"背景：{scenario}。")
        
        if i % 10 == 0: print(f"进度: {i}/{total_samples}...")
        answer = call_teacher(user_input)
        
        if answer:
            dataset.append({
                "messages": [
                    {"role": "system", "content": "你是专业A股AI产业链分析师。"},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": answer}
                ]
            })
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"完成！已生成 {len(dataset)} 条数据。")

if __name__ == "__main__":
    main()
