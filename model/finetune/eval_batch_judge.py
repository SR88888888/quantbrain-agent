import requests
import json
import re
import time
import random

VLLM_URL = "http://localhost:11434"
BASE_MODEL = "/datadisk/home/lsr/qwen2.5-72b-awq"
LORA_MODEL = "finance-lora"

TEST_CASES = [
    "分析寒武纪(688256.SH)，今日收盘价320元，涨跌幅+6.2%，量比2.8，RSI=78。背景：大基金三期追投半导体。",
    "分析科大讯飞(002230.SZ)，今日跌幅-4.1%，量比0.6，RSI=22。背景：主力资金连续3日净流出。",
    "分析中科曙光(603019.SH)，放量突破年线，涨幅+5.5%，所属AI算力板块普涨。",
    "分析奇安信(688561.SH)，缩量横盘震荡15个交易日，今日涨跌幅+0.1%，换手率仅0.8%。",
    "景嘉微(300474.SZ)突发利空，美国出口管制升级，今日开盘一字跌停，封单50万手。",
    "金山办公(688111.SH)公布三季报超预期，净利增长40%，但今日股价高开低走，收跌-2%。分析原因。",
    "海康威视(002415.SZ)RSI底背离，今日探底回升收长下影线，微涨1%。是否见底？",
    "今日AI产业链内部轮动，软件应用端大跌，但硬件算力端（如龙芯中科）逆势抗跌。给出策略。",
    "中科创达(300496.SZ)连收三根大阳线，偏离5日均线过远，且高管宣布减持计划。",
    "半导体板块迎政策利好，但大盘整体恐慌性杀跌，AI芯片个股多数冲高回落收绿。",
    "寒武纪(688256.SH)近期融券余额突增，且面临巨额解禁，技术面跌破支撑位。",
    "科大讯飞星火大模型V4.0发布，各项指标超预期，股价盘中瞬间拉升8%，随后迅速回落。",
    "中科曙光中标运营商智算中心百亿大单，股价一字涨停，量比放大至5.0以上。",
    "AI视觉龙头海康威视(002415.SZ)受外部制裁传闻影响，连续3日阴跌，MACD死叉。",
    "大盘极度缩量，AI安全板块异动，奇安信尾盘被资金突袭拉升4%，如何看待这种尾盘拉升？",
    "龙芯中科(688047.SH)新一代CPU流片成功，但前期股价已透支预期，今日利好兑现大跌。",
    "景嘉微(300474.SZ)日线级别KDJ金叉，成交量温和放大，但面临上方套牢盘重压区。",
    "外资（北向资金）今日大幅净买入金山办公(688111.SH) 5亿元，股价创年内新高。",
    "AI应用端集体杀跌，中科创达(300496.SZ)跌破发行价，但下方出现疑似机构托单。",
    "总结：今日政策面偏暖，但技术面A股整体承压，AI算力强于AI应用，请给出明日整体AI产业链的操作配置建议。"
]

def call_llm(model, prompt, temperature=0.1):
    try:
        resp = requests.post(f"{VLLM_URL}/v1/chat/completions", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 800
        }, timeout=120)
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def judge_responses(test_case, resp1, resp2):
    judge_prompt = f"""
你是一位极其严苛的顶级券商首席分析师。请评价以下两个AI对同一案例的分析。
案例：{test_case}

====================
分析师 A:
{resp1}

====================
分析师 B:
{resp2}
====================

请严格从以下三个维度对比：
1. 【废话率】：谁的套话更少，结论更直接果断？
2. 【专业度】：谁更好地结合了量价、指标与市场心理的因果关系？
3. 【研报风格】：谁的语气更像专业机构的内部投资策略（拒绝机器人口吻）？

请先简要点评，最后必须在新的一行严格输出结论格式：
如果A更好，输出：【最终获胜者：A】
如果B更好，输出：【最终获胜者：B】
如果一样好或一样差，输出：【最终获胜者：平局】
"""
    decision = call_llm(BASE_MODEL, judge_prompt, temperature=0.1)
    
    match = re.search(r'【最终获胜者：([AB平局]+)】', decision)
    if match:
        return match.group(1), decision
    return "解析失败", decision

def main():
    print(f"🚀 开始 20 题高强度盲测盲评 (Judge by {BASE_MODEL})\n")
    
    stats = {"Base_Wins": 0, "LoRA_Wins": 0, "Ties": 0, "Errors": 0}
    
    for i, case in enumerate(TEST_CASES, 1):
        print(f"▶ 正在测试 [{i}/20] ...")
        
        base_resp = call_llm(BASE_MODEL, case)
        lora_resp = call_llm(LORA_MODEL, case)
        
        if "ERROR" in base_resp or "ERROR" in lora_resp:
            print("  ❌ API 请求失败，跳过该题。")
            stats["Errors"] += 1
            continue

        is_base_a = random.choice([True, False])
        if is_base_a:
            resp_a, resp_b = base_resp, lora_resp
        else:
            resp_a, resp_b = lora_resp, base_resp

        winner_symbol, reason = judge_responses(case, resp_a, resp_b)
        
        if winner_symbol == "A":
            actual_winner = "Base" if is_base_a else "LoRA"
        elif winner_symbol == "B":
            actual_winner = "LoRA" if is_base_a else "Base"
        elif winner_symbol == "平局":
            actual_winner = "平局"
        else:
            actual_winner = "解析失败"

        if actual_winner == "Base":
            stats["Base_Wins"] += 1
            print("  🏆 胜者: 基础模型")
        elif actual_winner == "LoRA":
            stats["LoRA_Wins"] += 1
            print("  🏆 胜者: LoRA 模型")
        elif actual_winner == "平局":
            stats["Ties"] += 1
            print("  🤝 结果: 平局")
        else:
            stats["Errors"] += 1
            print("  ⚠️ 裁判未给出标准格式结论")
            
        time.sleep(0.5)

    print("\n" + "="*50)
    print("📊 批量评测最终结果")
    print("="*50)
    total_valid = 20 - stats["Errors"]
    print(f"总计成功判定: {total_valid} 题")
    print(f"Base 模型获胜: {stats['Base_Wins']} 题")
    print(f"LoRA 模型获胜: {stats['LoRA_Wins']} 题")
    print(f"平局数量: {stats['Ties']} 题")
    
    if total_valid > 0:
        lora_win_rate = (stats["LoRA_Wins"] / total_valid) * 100
        print(f"\n🎯 LoRA 净胜率 (不含平局): {lora_win_rate:.1f}%")
        
        if lora_win_rate >= 60:
            print("结论: ✅ 微调极其成功！LoRA 已经明显学到了垂直领域的分析逻辑，可直接上线。")
        elif lora_win_rate >= 40:
            print("结论: 🟡 微调初见成效，风格有所改变，但距离碾压基础模型还需要加大蒸馏数据量。")
        else:
            print("结论: ❌ 微调效果不佳，LoRA 在损失基础能力，强烈建议使用 500+ 高质量数据重新微调。")

if __name__ == "__main__":
    main()
