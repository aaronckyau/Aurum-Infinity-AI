"""
File Cache Manager - 靜態 HTML 快取管理
============================================================================
取代 SQLite 資料庫，改用靜態檔案儲存分析結果。

目錄結構（每個 ticker 一個資料夾）：
  cache/
    AAPL/
      info.json       ← 股票基本資料（名稱、交易所、時間戳記）
      biz.html        ← 商業模式分析（HTML）
      exec.html       ← 管理層分析（HTML）
      finance.html    ← 財務分析（HTML）
      call.html       ← 會議展望（HTML）
      ta_price.html   ← 技術面分析（HTML）
      ta_analyst.html ← 分析師預測（HTML）
      ta_social.html  ← 社群情緒（HTML）
    0700_HK/          ← 注意：點號換底線（避免檔案系統問題）
      info.json
      ...
============================================================================
"""

import json
import os
from datetime import datetime
from typing import Optional

# 合法的分析區塊白名單
VALID_SECTIONS = {'biz', 'exec', 'finance', 'call', 'ta_price', 'ta_analyst', 'ta_social'}

# 快取根目錄（與 app.py 同層）
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')


# ============================================================================
# 內部工具函數
# ============================================================================

def _safe_name(ticker: str) -> str:
    """
    將 ticker 轉為安全的資料夾名稱
    規則：點號換底線，全部大寫
    例：0700.HK → 0700_HK，601899.SS → 601899_SS，AAPL → AAPL
    """
    return ticker.upper().replace('.', '_')


def _ticker_dir(ticker: str) -> str:
    """取得 ticker 對應的快取資料夾路徑"""
    return os.path.join(CACHE_DIR, _safe_name(ticker))


def _info_path(ticker: str) -> str:
    """取得 info.json 的完整路徑"""
    return os.path.join(_ticker_dir(ticker), 'info.json')


def _html_path(ticker: str, section: str) -> str:
    """取得分析區塊 HTML 檔案的完整路徑"""
    return os.path.join(_ticker_dir(ticker), f'{section}.html')


# ============================================================================
# 公開 API
# ============================================================================

def get_stock(ticker: str) -> Optional[dict]:
    """
    讀取股票基本資料（info.json）

    Returns:
        包含 ticker / stock_name / chinese_name / exchange /
        created_at / updated_at 的字典；不存在則回傳 None
    """
    path = _info_path(ticker)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_section_html(ticker: str, section: str) -> Optional[str]:
    """
    讀取特定分析區塊的 HTML 內容

    Returns:
        HTML 字串；尚未分析則回傳 None
    """
    path = _html_path(ticker, section)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def save_stock(ticker: str, stock_name: str, chinese_name: str, exchange: str):
    """
    儲存（或更新）股票基本資料到 info.json
    若 info.json 已存在，保留原有的 created_at 時間戳記
    """
    ticker_dir = _ticker_dir(ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    now = datetime.now().isoformat()
    path = _info_path(ticker)

    # 保留原有的 created_at
    created_at = now
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        created_at = existing.get('created_at', now)

    data = {
        'ticker':       ticker.upper(),
        'stock_name':   stock_name,
        'chinese_name': chinese_name,
        'exchange':     exchange,
        'created_at':   created_at,
        'updated_at':   now,
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_section_html(ticker: str, section: str, html_content: str):
    """
    儲存分析區塊的 HTML 結果到 {section}.html
    同時更新 info.json 的 updated_at 時間戳記

    Args:
        ticker:       股票代碼（已標準化）
        section:      分析區塊名稱，需在 VALID_SECTIONS 內
        html_content: 已轉換好的 HTML 字串
    """
    if section not in VALID_SECTIONS:
        raise ValueError(f"非法的 section: {section}")

    ticker_dir = _ticker_dir(ticker)
    os.makedirs(ticker_dir, exist_ok=True)

    # 寫入 HTML 檔案
    with open(_html_path(ticker, section), 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 更新 info.json 的 updated_at
    info_path = _info_path(ticker)
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['updated_at'] = datetime.now().isoformat()
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
