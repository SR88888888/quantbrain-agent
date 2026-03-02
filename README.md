# 稷下智脑 · QuantBrain Agent

> 基于 Qwen2.5-72B-AWQ 的全链路 A 股 AI 产业链投研系统

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![vLLM](https://img.shields.io/badge/vLLM-LoRA-orange.svg)](https://github.com/vllm-project/vllm)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 项目简介

稷下智脑是一套面向 A 股 AI 产业链投研场景的**全链路自动化系统**。针对传统投研时效差、逻辑碎片化、数据难量化等核心痛点，系统以 Qwen2.5-72B-AWQ 为推理内核，通过 LangGraph 编排六路智能体协作流，融合 LoRA 垂直微调、MCP 工具链与 CoT+ReAct 混合推理架构，实现从实时行情舆情采集、产业链知识图谱多维推演，到 Reflexion 反思审核的投研全闭环，每日 9:00 定时产出机构级专业研报并推送飞书。

**LoRA 微调经 20 题盲测评定，净胜率 65%，已验证垂直领域分析能力显著提升。**

---

## 核心架构

```
采集 (Collector)
    ↓
舆情分析 (Sentiment) ─┐
行业分析 (Sector)    ─┼─→ 协调 (Supervisor) → 编撰 (Writer) → 审核 (Reviewer)
宏观分析 (Macro)    ─┘                                              ↓
                                                              推送 (Feishu)
                                                                   ↓
                                                            反思 (Reflexion)
```

**1+3+1+1 多智能体架构**：1 个采集节点 → 3 路并行分析 → 1 个 Supervisor 协调 → 1 个编撰审核闭环

---

## 技术亮点

### 🔬 量化微调 · LoRA on AWQ
- 基于 Qwen2.5-72B-AWQ 使用 autoawq 原生加载，通过 PEFT 挂载 LoRA 适配器（r=8，target: q_proj/v_proj）
- 72B 大模型自蒸馏生成 2000 条 A 股多因子分析语料（覆盖超买异动、放量突破、事件驱动、板块轮动等 6 类场景）
- vLLM 动态加载 LoRA，零侵入切换基础/微调模型
- **20 题盲测评定净胜率 65%**，强化金融分析深度与专业表达

### 🕸️ 知识图谱 · 产业链联动
- 内置 AI 产业链知识图谱（10 只核心标的 × 6 类产业链关系），存储于 SQLite
- SectorAgent 实时计算同板块、上下游标的走势分化信号
- 支持按板块检索概念股、关联标的关系推演

### 🧠 混合推理 · CoT + ReAct + Reflexion
- **CoT**：5 步结构化思维链，覆盖舆情/板块/宏观/报告编撰/质量审核 5 个 domain
- **ReAct**：思考-行动-观察循环，通过 MCP 工具动态调用行情、资金流向、知识图谱等数据
- **Reflexion**：审核问题沉淀为历史经验，注入下次编撰提示词，持续消除逻辑缺陷

### 🔧 MCP 工具链 · 标准插件体系
- 引入 MCP 协议构建工具注册表，封装 9 项原子工具：

| 工具 | 能力 |
|---|---|
| `stock_get_quote` | 实时行情查询 |
| `stock_batch_quotes` | 批量行情获取 |
| `stock_fund_flow` | 主力资金流向 |
| `stock_get_news` | 个股新闻采集 |
| `market_overview` | 大盘/板块/北向资金 |
| `knowledge_query` | 知识图谱检索 |
| `knowledge_sector_stocks` | 板块概念股列表 |
| `memory_search` | 历史记忆搜索 |
| `memory_add` | 记忆写入 |

### 📊 多源采集 · 实时数据管线
- 东方财富 + 新浪财经双源异步抓取，BS4 自动提取新闻正文（最多并发 5 路）
- AKShare 历史行情 + 东财推送接口实时行情，无真实数据标的自动跳过（不注入 Mock 数据）
- 数据质量加权评分，正文覆盖率、真实行情覆盖率动态影响下游分析置信度

### ⏰ 全链路自动化
- APScheduler 驱动，工作日 9:00 自动触发研报任务
- 飞书 Webhook 秒级推送，支持卡片格式富文本
- Docker 容器化部署，云端全时无人值守运行

---

## 监控标的

系统聚焦 A 股 AI 产业链 10 只核心标的：

| 代码 | 名称 | 板块 |
|---|---|---|
| 002230.SZ | 科大讯飞 | AI应用 |
| 300474.SZ | 景嘉微 | AI芯片 |
| 688111.SH | 金山办公 | AI应用 |
| 688047.SH | 龙芯中科 | AI芯片 |
| 002415.SZ | 海康威视 | AI视觉 |
| 688256.SH | 寒武纪 | AI芯片 |
| 603019.SH | 中科曙光 | AI算力 |
| 688396.SH | 华峰测控 | AI芯片 |
| 300496.SZ | 中科创达 | AI应用 |
| 688561.SH | 奇安信 | AI安全 |

---

## 目录结构

```
quantbrain-agent/
├── main.py                    # 入口，启动时生成测试报告 + 调度器
├── src/
│   ├── agents/                # 六路智能体
│   │   ├── collector.py       # 数据采集
│   │   ├── sentiment.py       # 舆情分析（CoT + Skill）
│   │   ├── sector.py          # 板块分析（ReAct + 知识图谱）
│   │   ├── macro.py           # 宏观解读（CoT）
│   │   ├── writer.py          # 研报编撰（深度 Prompt + Reflexion）
│   │   ├── reviewer.py        # 质量审核（规则 + CoT）
│   │   └── supervisor.py      # 结果合并与冲突裁决
│   ├── workflow/
│   │   └── daily_report.py    # LangGraph 主工作流
│   ├── mcp/                   # MCP 工具注册表与实现
│   ├── reasoning/             # CoT / ReAct / Reflexion
│   ├── memory/                # 记忆存储 + 知识图谱（SQLite）
│   ├── data/                  # 爬虫 + 清洗 + 数据源聚合
│   ├── llm/                   # LLM 封装 + Prompt 模板
│   ├── skills/                # Skill 管理器（JSON 结构化输出）
│   ├── push/                  # 飞书 / 企微 / 邮件推送
│   └── scheduler/             # APScheduler 定时任务
├── model/
│   ├── finetune/              # LoRA 微调脚本
│   │   ├── train_lora.py      # AWQ + LoRA 训练
│   │   └── final_miner.py     # 自蒸馏数据生成
│   └── serve/
│       └── inference_api.py   # FastAPI 推理接口
├── finetune_data_2000.json    # 2000 条自蒸馏训练语料
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## 快速开始

### 环境要求
- Python 3.10+
- vLLM（已部署 Qwen2.5-72B-AWQ）
- CUDA GPU（训练需要，推理通过 vLLM 服务）

### 安装依赖

```bash
git clone https://github.com/SR88888888/quantbrain-agent.git
cd quantbrain-agent
pip install -r requirements.txt
```

### 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
LLM_BASE_URL=http://localhost:11434
MODEL_NAME=/path/to/qwen2.5-72b-awq
PUSH_FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/...
```

### 启动 vLLM（含 LoRA）

```bash
vllm serve /path/to/qwen2.5-72b-awq \
    --host 0.0.0.0 --port 11434 \
    --enable-lora \
    --lora-modules finance-lora=qwen2.5-72b-awq-lora \
    --max-lora-rank 8
```

### 运行系统

```bash
python main.py
```

启动时自动生成一次收盘研报，随后挂载定时调度器。

### Docker 部署

```bash
docker-compose up -d
```

---

## LoRA 微调复现

### 1. 生成训练数据（自蒸馏）

```bash
python train_dist.py
# 输出: finetune_data_2000.json（约 2000 条多场景分析语料）
```

### 2. 训练 LoRA

```bash
cd model/finetune
python train_lora.py
# 输出: qwen2.5-72b-awq-lora/
```

### 3. 评估效果

```bash
python model/finetune/final_miner.py
# 规则打分 + 72B Judge 盲测双重评估
```

**评测结果（20 题盲测）：**
```
Base 模型获胜：7 题
LoRA 模型获胜：13 题
LoRA 净胜率：65%  ✅ 微调极其成功
```

---

## 研报样例输出

```
要点速览
• 市场情绪回暖
• AI芯片领涨

摘要: 市场情绪中性偏弱，AI芯片板块表现强劲，寒武纪-U和科大讯飞成为市场焦点。

一、市场概览
AI芯片 +7.96% | AI算力 +1.56% | AI应用 -0.77%

二、核心个股分析
寒武纪-U (688256.SH): 涨幅7.96%，主力资金集中流入，RSI=72，
短期强势信号明确，产业链国产替代逻辑持续兑现...

（全文 1500-2500 字，覆盖 10 只标的逐一分析）
```

---

## 技术栈

`Python` `FastAPI` `LangGraph` `Qwen2.5-72B-AWQ` `vLLM` `LoRA/PEFT` `PyTorch` `AKShare` `BeautifulSoup4` `httpx` `SQLite` `APScheduler` `Docker` `Linux`

---

## 免责声明

本项目为技术研究项目，所有分析内容均由 AI 自动生成，**不构成任何投资建议**。投资有风险，入市需谨慎。

---

## License

[MIT](LICENSE)
