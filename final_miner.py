import pandas as pd
import re
import json
import time
from openai import OpenAI
from config import Config
from tqdm import tqdm

def mine():
    print("💎 启动稳健版数据炼金引擎 (串行模式)...")
    client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_API_URL)
    
    df = pd.read_csv(Config.PUBLICATIONS_FILE)
    # 缩小范围，只找标记为有阿卡德语的页面
    target_pages = df[df['has_akkadian'].astype(str).str.upper() == 'TRUE']['page_text'].dropna().tolist()
    
    results = []
    # 限制扫描页数，先保质保量挖出 2000 页的精华
    max_pages = 5000 
    
    pbar = tqdm(total=min(len(target_pages), max_pages))
    
    for text in target_pages[:max_pages]:
        # 预过滤：如果页面连个连字符都没有，直接跳过
        if '-' not in text:
            pbar.update(1)
            continue
            
        # 抽取中间最可能有内容的 800 字符
        mid = len(text) // 2
        snip = text[max(0, mid-400):min(len(text), mid+400)]
        
        prompt = (
            "Extract Akkadian-English translation pairs from this OCR. "
            "Translate German/French to English. Return ONLY a JSON list: [{\"src\":\"...\",\"tgt\":\"...\"}]. "
            "Text: " + snip
        )
        
        try:
            resp = client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=20.0
            )
            content = resp.choices[0].message.content
            match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                for item in data:
                    if 'src' in item and 'tgt' in item:
                        results.append({'source': item['src'], 'target': item['tgt']})
        except Exception:
            # 即使单条失败也继续下一条，不中断
            time.sleep(1) 
            
        pbar.update(1)
        
        # 每挖到 50 条存一次盘，确保安全
        if len(results) > 0 and len(results) % 50 == 0:
            pd.DataFrame(results).drop_duplicates(subset=['source']).to_csv("massive_raw_data.csv", index=False)

    final_df = pd.DataFrame(results).drop_duplicates(subset=['source'])
    final_df.to_csv("massive_raw_data.csv", index=False)
    print(f"\n✅ 炼金完成! 获得高质量语料: {len(final_df)} 条")

if __name__ == "__main__":
    mine()
