"""技能定义: Prompt模板和输出Schema"""


SKILL_DEFINITIONS = {
    "sentiment_scoring": {
        "name": "情绪评分",
        "required_params": ["symbol", "news_titles"],
        "prompt": (
            "分析新闻情绪,返回JSON:\n"
            "股票: {symbol}\n新闻: {news_titles}\n\n"
            '返回格式:\n'
            '{{"positive_score": 0-100, "negative_score": 0-100, '
            '"overall_score": -100到100, "keywords": ["关键词"], "confidence": 0.0-1.0}}'
        ),
        "output_schema": {
            "required": ["overall_score", "confidence"],
            "defaults": {"positive_score": 50, "negative_score": 50, "keywords": []},
        },
    },
    "trend_analysis": {
        "name": "趋势分析",
        "required_params": ["symbol", "price", "change_pct", "volume"],
        "prompt": (
            "分析股票趋势,返回JSON:\n"
            "股票: {symbol}, 价格: {price}, 涨跌: {change_pct}%, 成交量: {volume}\n\n"
            '返回格式:\n'
            '{{"trend": "上升/下降/横盘", "strength": "强/中/弱", '
            '"confidence": 0.0-1.0, "reason": "简短理由"}}'
        ),
        "output_schema": {
            "required": ["trend", "confidence"],
            "defaults": {"strength": "中", "reason": ""},
        },
    },
    "news_summarize": {
        "name": "新闻摘要",
        "required_params": ["news_text"],
        "prompt": (
            "将以下新闻提炼为简洁摘要,返回JSON:\n"
            "{news_text}\n\n"
            '返回格式:\n'
            '{{"summary": "50字摘要", "key_points": ["要点1", "要点2"], '
            '"confidence": 0.0-1.0}}'
        ),
        "output_schema": {
            "required": ["summary", "confidence"],
            "defaults": {"key_points": []},
        },
    },
    "report_section": {
        "name": "报告段落",
        "required_params": ["topic", "data_context"],
        "prompt": (
            "根据以下数据为研报生成一个段落,返回JSON:\n"
            "主题: {topic}\n数据: {data_context}\n\n"
            '返回格式:\n'
            '{{"title": "段落标题", "body": "200字以内正文", '
            '"highlights": ["要点1", "要点2"], "confidence": 0.0-1.0}}'
        ),
        "output_schema": {
            "required": ["title", "body", "confidence"],
            "defaults": {"highlights": []},
        },
    },
    "fact_check": {
        "name": "事实核查",
        "required_params": ["claim", "source_data"],
        "prompt": (
            "核查以下陈述的准确性,返回JSON:\n"
            "陈述: {claim}\n数据来源: {source_data}\n\n"
            '返回格式:\n'
            '{{"is_accurate": true/false, "issues": ["问题1"], '
            '"suggestion": "修改建议", "confidence": 0.0-1.0}}'
        ),
        "output_schema": {
            "required": ["is_accurate", "confidence"],
            "defaults": {"issues": [], "suggestion": ""},
        },
    },
}
