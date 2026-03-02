"""
AI产业链金融写作微调数据生成
适配模型: Qwen2.5-72B-AWQ (vLLM serving)
数据来源: akshare行情 + 模板化分析文本
"""
import json
import random
from datetime import datetime, timedelta

OUTPUT_PATH = "finetune_data.json"

STOCK_LIST = [
    ("002230.SZ", "科大讯飞", "AI应用"),
    ("300474.SZ", "景嘉微", "AI芯片"),
    ("688111.SH", "金山办公", "AI应用"),
    ("688047.SH", "龙芯中科", "AI芯片"),
    ("002415.SZ", "海康威视", "AI视觉"),
    ("688256.SH", "寒武纪", "AI芯片"),
    ("603019.SH", "中科曙光", "AI算力"),
    ("688396.SH", "华峰测控", "AI芯片"),
    ("300496.SZ", "中科创达", "AI应用"),
    ("688561.SH", "奇安信", "AI安全"),
]


def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def generate_analysis_sample(symbol, name, sector, rsi, change_pct, volume_ratio):
    user_content = (
        f"请分析AI概念股{name}({symbol})的当前状态:\n"
        f"所属板块: {sector}\n"
        f"RSI={rsi}, 涨跌幅={change_pct:.2f}%, 量比={volume_ratio:.2f}"
    )

    parts = []
    if rsi > 70:
        parts.append(f"RSI指标{rsi}已进入超买区域(>70),短期存在回调压力。")
        signal = "偏空"
    elif rsi < 30:
        parts.append(f"RSI指标{rsi}处于超卖区域(<30),技术面存在反弹需求。")
        signal = "偏多"
    else:
        parts.append(f"RSI指标{rsi}处于中性区域,技术面空间较为充足。")
        signal = "中性"

    if change_pct > 3:
        parts.append(f"今日涨幅{change_pct:.2f}%,表现强势。")
    elif change_pct < -3:
        parts.append(f"今日跌幅{change_pct:.2f}%,走势偏弱。")
    else:
        parts.append(f"今日涨跌幅{change_pct:.2f}%,波动平稳。")

    if volume_ratio > 1.5:
        parts.append("成交量明显放大,资金活跃度提升。")
    elif volume_ratio < 0.7:
        parts.append("成交量萎缩,市场观望情绪较浓。")

    analysis = "\n".join(parts)
    summary = f"综合来看,{name}当前技术面信号{signal},作为{sector}核心标的,建议关注产业政策催化和量能变化。"

    assistant_content = (
        f"{name}({symbol}) {sector}板块 技术分析\n\n"
        f"{analysis}\n\n"
        f"总结: {summary}"
    )

    return {
        "messages": [
            {"role": "system", "content": "你是专业A股AI产业链分析师,擅长技术分析和产业链研究。输出格式为纯文本。"},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


def generate_data():
    try:
        import akshare as ak
        print("使用akshare获取真实数据...")
    except ImportError:
        print("akshare未安装,使用Mock数据")
        return generate_mock_data()

    training_data = []

    for idx, (symbol, name, sector) in enumerate(STOCK_LIST):
        print(f"[{idx + 1}/{len(STOCK_LIST)}] 处理 {name}({symbol})...")
        try:
            code = symbol.split(".")[0]
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

            if df is None or len(df) < 30:
                print(f"  数据不足,使用Mock")
                training_data.extend(generate_mock_samples(symbol, name, sector, 30))
                continue

            df = df.sort_values("日期").reset_index(drop=True)
            count = 0

            for i in range(30, len(df), 5):
                prices = df["收盘"].iloc[i - 30: i].tolist()
                rsi = calculate_rsi(prices)
                change_pct = df["涨跌幅"].iloc[i] if "涨跌幅" in df.columns else 0
                vol_ma = df["成交量"].iloc[i - 5: i].mean()
                volume_ratio = df["成交量"].iloc[i] / vol_ma if vol_ma > 0 else 1

                sample = generate_analysis_sample(symbol, name, sector, rsi, change_pct, volume_ratio)
                training_data.append(sample)
                count += 1

            print(f"  生成 {count} 条样本")

        except Exception as e:
            print(f"  错误: {e}, 使用Mock")
            training_data.extend(generate_mock_samples(symbol, name, sector, 30))

    return training_data


def generate_mock_samples(symbol, name, sector, n=30):
    samples = []
    for _ in range(n):
        sample = generate_analysis_sample(
            symbol, name, sector,
            round(random.uniform(20, 80), 1),
            random.uniform(-5, 5),
            random.uniform(0.5, 2.5),
        )
        samples.append(sample)
    return samples


def generate_mock_data():
    print("使用Mock数据生成训练样本...")
    training_data = []
    for symbol, name, sector in STOCK_LIST:
        training_data.extend(generate_mock_samples(symbol, name, sector, 50))
        print(f"  {name}({symbol}): 50条样本")
    return training_data


def main():
    print("=" * 60)
    print("生成AI产业链金融写作微调数据")
    print("=" * 60)

    training_data = generate_data()
    random.shuffle(training_data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"完成: {len(training_data)} 条样本 -> {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
