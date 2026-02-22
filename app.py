"""
Stock Analyzer - 主程式（Google Gemini 3 Flash 版本 + 資料庫快取）
============================================================================
API：Google Gemini API + Google Search Grounding（自帶網絡搜索）
  - 模型：gemini-2.0-flash (或 gemini-3-flash-preview)
  - SDK：google-genai
  - 資料庫：SQLite（避免重複呼叫 API，節省成本）
============================================================================
"""
from dotenv import load_dotenv
import os
import re
import time
from datetime import datetime
from typing import Dict

import markdown
import requests
from flask import Flask, render_template, request, jsonify

from google import genai
from google.genai import types

from prompt_manager import PromptManager
from database import StockDatabase

# ============================================================================
# Configuration
# ============================================================================
load_dotenv()   

class Config:
    # -----------------------------------------------------------------------
    # Google Gemini API 設定
    # -----------------------------------------------------------------------
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-3-flash-preview"

    # -----------------------------------------------------------------------
    # Financial Modeling Prep API (用於基礎名稱檢索)
    # -----------------------------------------------------------------------
    FMP_API_KEY = os.getenv("FMP_API_KEY")

    REQUEST_TIMEOUT = 7
    DEFAULT_TICKER = 'NVDA'
    PROMPTS_PATH = os.path.join(os.path.dirname(__file__), 'prompts', 'prompts.yaml')

    # API 請求設定
    API_MAX_TOKENS = 8000
    API_MAX_RETRIES = 2
    API_RETRY_DELAY = 5

    # -----------------------------------------------------------------------
    # 美股交易所列表（這些交易所不需要呼叫 AI 取中文名）
    # -----------------------------------------------------------------------
    US_EXCHANGES = {'NYSE', 'NASDAQ', 'AMEX', 'NYSEArca', 'BATS', 'OTC'}


app = Flask(__name__)
today = datetime.now().strftime('%Y/%m/%d')

# ============================================================================
# 初始化 Gemini Client、PromptManager 與 Database
# ============================================================================
gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
prompt_manager = PromptManager(Config.PROMPTS_PATH)
db = StockDatabase()

# ============================================================================
# Gemini API Functions
# ============================================================================

def call_gemini_api(prompt: str, use_search: bool = True) -> str:
    """調用 Gemini API，支援聯網搜索"""
    config_params = {
        "temperature": 0.7,
        "max_output_tokens": Config.API_MAX_TOKENS,
    }

    if use_search:
        config_params["tools"] = [
            types.Tool(google_search=types.GoogleSearch())
        ]

    config = types.GenerateContentConfig(**config_params)

    for attempt in range(Config.API_MAX_RETRIES + 1):
        try:
            response = gemini_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )

            if response.text:
                return response.text
            else:
                return "⚠️ API 回覆為空或被安全過濾。"

        except Exception as e:
            print(f"[Gemini] Error: {e}")
            if attempt < Config.API_MAX_RETRIES:
                time.sleep(Config.API_RETRY_DELAY)
                continue
            return f"⚠️ API 錯誤: {str(e)}"

    return "⚠️ API 請求失敗。"

# ============================================================================
# Ticker 標準化
# ============================================================================

def normalize_ticker(ticker: str) -> str:
    """
    標準化股票代碼
    
    規則：
      - 1~4 位純數字 → 港股：補零到 4 位 + .HK
        例：700 → 0700.HK, 9 → 0009.HK, 388 → 0388.HK, 1810 → 1810.HK
      - 5 位以上純數字 → A 股：原樣保留（交給 get_stock_name 前綴匹配）
        例：601899 → 601899, 000001 → 000001
      - 已有 .HK / .SS / .SZ 後綴 → 原樣保留
        例：0700.HK → 0700.HK, 601899.SS → 601899.SS
      - 英文字母開頭 → 美股：原樣保留
        例：AAPL → AAPL, TSLA → TSLA
    """
    raw = ticker.upper().strip()
    
    # 已有後綴（.HK / .SS / .SZ / .T 等）→ 不處理
    if '.' in raw:
        print(f"[normalize] 已有後綴: {raw}")
        return raw
    
    # 純數字 → 判斷位數
    if raw.isdigit():
        if len(raw) <= 4:
            # 1~4 位數字 → 港股，補零到 4 位 + .HK
            normalized = raw.zfill(4) + '.HK'
            print(f"[normalize] 港股補零: {ticker} → {normalized}")
            return normalized
        else:
            # 5 位以上 → A 股（不加後綴，交給 get_stock_name 前綴匹配）
            print(f"[normalize] A 股: {raw}")
            return raw
    
    # 英文或其他 → 美股，原樣保留
    print(f"[normalize] 美股/其他: {raw}")
    return raw

# ============================================================================
# Data Functions
# ============================================================================

def get_stock_name(ticker: str) -> tuple:
    """
    獲取公司完整名稱與交易所
    
    匹配邏輯（按優先級）：
      1. 精確匹配：輸入 AAPL → 匹配 AAPL
      2. 帶後綴匹配：輸入 0700.HK → 匹配 0700.HK
      3. 模糊匹配：輸入 601899 → 匹配 601899.SS（A 股）
         - 適用場景：用戶輸入純數字代碼但不帶 .SS / .SZ 後綴
    """
    url = f"https://financialmodelingprep.com/stable/search-symbol?query={ticker}&apikey={Config.FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
        data = response.json()
        
        if not data or not isinstance(data, list):
            print(f"[get_stock_name] No data for {ticker}")
            return None, None
        
        ticker_upper = ticker.upper().strip()
        
        # === 第 1 輪：精確匹配（AAPL → AAPL, 0700.HK → 0700.HK）===
        for item in data:
            symbol = item.get('symbol', '').upper().strip()
            if symbol == ticker_upper:
                name = item.get('name', '').strip()
                exchange = item.get('exchange', '').strip()
                if name:
                    print(f"[get_stock_name] 精確匹配: {ticker} → {symbol} = {name} ({exchange})")
                    return name, exchange
        
        # === 第 2 輪：前綴匹配（601899 → 601899.SS, 000001 → 000001.SZ）===
        # 只在用戶輸入不含 "." 時啟用（避免 0700.HK 誤匹配到其他東西）
        if '.' not in ticker_upper:
            best_match = None
            for item in data:
                symbol = item.get('symbol', '').upper().strip()
                if symbol.startswith(ticker_upper + '.'):
                    name = item.get('name', '').strip()
                    exchange = item.get('exchange', '').strip()
                    if name:
                        if best_match is None:
                            best_match = (name, exchange, symbol)
                        elif exchange in ('SHH', 'SHZ') and best_match[1] not in ('SHH', 'SHZ'):
                            best_match = (name, exchange, symbol)
            
            if best_match:
                print(f"[get_stock_name] 前綴匹配: {ticker} → {best_match[2]} = {best_match[0]} ({best_match[1]})")
                return best_match[0], best_match[1]
        
        print(f"[get_stock_name] No match for {ticker}")
        return None, None
        
    except Exception as e:
        print(f"[get_stock_name] Error: {e}")
        return None, None


def is_us_stock(exchange: str) -> bool:
    """判斷是否為美股（根據交易所代碼）"""
    return exchange.upper().strip() in Config.US_EXCHANGES


def get_chinese_name(english_name: str, ticker: str, exchange: str) -> str:
    """
    取得公司的繁體中文名稱
    
    邏輯：
      - 美股（NYSE / NASDAQ 等）→ 直接回傳英文名，不呼叫 AI（節省成本）
      - 港股 / A 股 / 其他      → 呼叫 Gemini API 取得官方中文名稱
    """
    if is_us_stock(exchange):
        print(f"[get_chinese_name] 美股 {ticker}（{exchange}），跳過 AI，使用英文名")
        return english_name
    
    print(f"[get_chinese_name] 非美股 {ticker}（{exchange}），呼叫 AI 取中文名")
    prompt = (
        f"公司：{english_name} ({ticker})，交易所：{exchange}。\n"
        f"請只回覆這家公司的官方繁體中文名稱，不要任何解釋。不要包含股票代碼或交易所名稱, 不要有限公司等字樣，直接回覆核心名稱即可。"
    )
    return call_gemini_api(prompt, use_search=False).strip()

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    raw_ticker = request.args.get('ticker', Config.DEFAULT_TICKER).strip()
    ticker = normalize_ticker(raw_ticker)  # ★ 標準化：700 → 0700.HK
    
    # ★ 先檢查資料庫是否有快取
    cached_data = db.get_stock(ticker)
    
    if cached_data:
        print(f"[DB] 從資料庫載入 {ticker}")
        
        cached_sections_html = {}
        for section_key in ['biz', 'finance', 'valuation', 'tech', 'sentiment', 'risk', 'strategy']:
            if cached_data.get(section_key):
                cached_sections_html[section_key] = markdown.markdown(
                    cached_data[section_key],
                    extensions=['tables', 'fenced_code', 'nl2br']
                )
        
        return render_template(
            'index.html',
            ticker=ticker,
            stock_name=cached_data['stock_name'],
            chinese_name=cached_data['chinese_name'],
            m={"eps": "-", "pe": "-", "yield": "-", "short": "-", "cap": "-", "vol": "-"},
            date=today,
            sections=prompt_manager.get_section_names(),
            cached_sections=cached_sections_html
        )
    
    # 沒有快取，查詢 API
    stock_name, exchange = get_stock_name(ticker)
    
    if stock_name is None:
        return render_template('error.html', ticker=raw_ticker, date=today), 404

    chinese_name = get_chinese_name(stock_name, ticker, exchange)
    
    # ★ 儲存基本資料到資料庫
    db.save_stock(
        ticker=ticker,
        stock_name=stock_name,
        chinese_name=chinese_name,
        exchange=exchange,
        sections={}
    )
    
    metrics = {
        "eps": "-", "pe": "-", "yield": "-", 
        "short": "-", "cap": "-", "vol": "-"
    }

    return render_template(
        'index.html',
        ticker=ticker,
        stock_name=stock_name,
        chinese_name=chinese_name,
        m=metrics,
        date=today,
        sections=prompt_manager.get_section_names(),
        cached_sections=None
    )


@app.route('/analyze/<section>', methods=['POST'])
def analyze_section(section):
    raw_ticker = request.json.get('ticker', '')
    ticker = normalize_ticker(raw_ticker)  # ★ 標準化
    force_update = request.json.get('force_update', False)
    
    # ★ 如果不是強制更新，先檢查資料庫
    if not force_update:
        cached_data = db.get_stock(ticker)
        if cached_data and cached_data.get(section):
            print(f"[DB] 從資料庫載入 {ticker} - {section}")
            html_content = markdown.markdown(
                cached_data[section],
                extensions=['tables', 'fenced_code', 'nl2br']
            )
            return jsonify({
                "success": True,
                "report": html_content,
                "from_cache": True
            })
    
    # ★ 需要呼叫 AI（首次查詢或強制更新）
    stock_name, exchange = get_stock_name(ticker)

    if stock_name is None:
        return jsonify({"success": False, "error": f"找不到 {ticker} 的資料"})

    chinese_name = get_chinese_name(stock_name, ticker, exchange)

    try:
        prompt = prompt_manager.build(
            section=section,
            ticker=ticker,
            stock_name=stock_name,
            exchange=exchange,
            today=today,
            chinese_name=chinese_name,
        )

        print(f"[AI] 呼叫 AI 分析 {ticker} - {section}")
        response_text = call_gemini_api(prompt, use_search=True)

        # ★ 儲存到資料庫
        db.update_section(ticker, section, response_text)

        html_content = markdown.markdown(
            response_text,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

        return jsonify({
            "success": True,
            "report": html_content,
            "from_cache": False
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
