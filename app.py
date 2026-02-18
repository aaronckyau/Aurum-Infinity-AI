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


app = Flask(__name__)
today = datetime.now().strftime('%Y/%m/%d')

# ============================================================================
# 初始化 Gemini Client、PromptManager 與 Database
# ============================================================================
gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
prompt_manager = PromptManager(Config.PROMPTS_PATH)
db = StockDatabase()  # ★ 新增：初始化資料庫

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
# Data Functions
# ============================================================================

def get_stock_name(ticker: str) -> tuple:
    """獲取公司完整名稱與交易所（精確匹配 ticker）"""
    url = f"https://financialmodelingprep.com/stable/search-symbol?query={ticker}&apikey={Config.FMP_API_KEY}"
    try:
        response = requests.get(url, timeout=Config.REQUEST_TIMEOUT)
        data = response.json()
        
        if not data or not isinstance(data, list):
            print(f"[get_stock_name] No data for {ticker}")
            return None, None
        
        for item in data:
            symbol = item.get('symbol', '').upper().strip()
            if symbol == ticker.upper().strip():
                name = item.get('name', '').strip()
                exchange = item.get('exchange', '').strip()
                if name:
                    print(f"[get_stock_name] Match: {ticker} -> {name} ({exchange})")
                    return name, exchange
        
        print(f"[get_stock_name] No exact match for {ticker}")
        return None, None
        
    except Exception as e:
        print(f"[get_stock_name] Error: {e}")
        return None, None


def get_chinese_name(english_name: str, ticker: str, exchange: str) -> str:
    """透過 Gemini 取得公司繁體中文名稱"""
    prompt = (
        f"公司：{english_name} ({ticker})，交易所：{exchange}。\n"
        f"請只回覆這家公司的官方繁體中文名稱，不要任何解釋。"
    )
    return call_gemini_api(prompt, use_search=False).strip()

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    ticker = request.args.get('ticker', Config.DEFAULT_TICKER).upper().strip()
    
    # ★ 先檢查資料庫是否有快取
    cached_data = db.get_stock(ticker)
    
    if cached_data:
        # 從資料庫載入
        print(f"[DB] 從資料庫載入 {ticker}")
        
        # 將 Markdown 轉為 HTML
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
            cached_sections=cached_sections_html  # ★ 傳遞快取資料（已轉 HTML）
        )
    
    # 沒有快取，查詢 API
    stock_name, exchange = get_stock_name(ticker)
    
    if stock_name is None:
        return render_template('error.html', ticker=ticker, date=today), 404

    chinese_name = get_chinese_name(stock_name, ticker, exchange)
    
    # ★ 儲存基本資料到資料庫（但分析內容還是空的）
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
        cached_sections=None  # 沒有快取
    )


@app.route('/analyze/<section>', methods=['POST'])
def analyze_section(section):
    ticker = request.json.get('ticker')
    force_update = request.json.get('force_update', False)  # ★ 是否強制更新
    
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
                "from_cache": True  # ★ 標記來自快取
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
            "from_cache": False  # ★ 標記來自 AI
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)