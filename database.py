"""
Database Manager - 股票分析資料庫管理
============================================================================
使用 SQLite 儲存股票分析結果，避免重複呼叫 API
============================================================================
"""

import sqlite3
from datetime import datetime
from typing import Dict, Optional


class StockDatabase:
    """股票分析資料庫管理類別"""

    def __init__(self, db_path: str = "stock_analysis.db"):
        """
        初始化資料庫連線
        
        Args:
            db_path: 資料庫檔案路徑
        """
        self.db_path = db_path
        self._create_table()
        self._migrate()  # ★ 啟動時自動檢查並執行遷移

    def _create_table(self):
        """建立資料表（如果不存在）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_analysis (
                ticker TEXT PRIMARY KEY,
                stock_name TEXT NOT NULL,
                chinese_name TEXT,
                exchange TEXT NOT NULL,
                biz TEXT,
                exec TEXT,
                finance TEXT,
                call TEXT,
                ta_price TEXT,
                ta_analyst TEXT,
                ta_social TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

    def _migrate(self):
        """
        資料庫遷移 — 自動處理欄位重命名
        
        每次啟動時檢查，已遷移過的不會重複執行。
        如果未來有新的遷移需求，在這裡繼續加即可。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 取得目前所有欄位名稱
        cursor.execute('PRAGMA table_info(stock_analysis)')
        columns = [row[1] for row in cursor.fetchall()]
        
        # ---------------------------------------------------------------
        # 遷移 1：ta_option → ta_analyst（2026/02）
        # ---------------------------------------------------------------
        if 'ta_option' in columns and 'ta_analyst' not in columns:
            print("[DB Migration] 正在重命名欄位: ta_option → ta_analyst")
            cursor.execute('ALTER TABLE stock_analysis RENAME COLUMN ta_option TO ta_analyst')
            conn.commit()
            print("[DB Migration] ✅ 遷移完成，舊資料已保留")
        
        # ---------------------------------------------------------------
        # 未來的遷移可以繼續加在這裡，例如：
        # if 'old_column' in columns and 'new_column' not in columns:
        #     cursor.execute('ALTER TABLE ... RENAME COLUMN ...')
        # ---------------------------------------------------------------
        
        conn.close()

    def get_stock(self, ticker: str) -> Optional[Dict]:
        """
        從資料庫取得股票分析資料
        
        Args:
            ticker: 股票代碼
            
        Returns:
            包含所有分析結果的字典，如果不存在則回傳 None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM stock_analysis WHERE ticker = ?',
            (ticker.upper(),)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None

    def save_stock(
        self,
        ticker: str,
        stock_name: str,
        chinese_name: str,
        exchange: str,
        sections: Dict[str, str]
    ):
        """
        儲存或更新股票分析資料
        
        Args:
            ticker: 股票代碼
            stock_name: 英文名稱
            chinese_name: 中文名稱
            exchange: 交易所
            sections: 各分析區塊的結果 {"biz": "...", "finance": "...", ...}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            'SELECT ticker FROM stock_analysis WHERE ticker = ?',
            (ticker.upper(),)
        )
        exists = cursor.fetchone() is not None
        
        if exists:
            update_fields = []
            values = []
            
            update_fields.append('stock_name = ?')
            values.append(stock_name)
            
            update_fields.append('chinese_name = ?')
            values.append(chinese_name)
            
            update_fields.append('exchange = ?')
            values.append(exchange)
            
            for section_key, content in sections.items():
                if content:
                    update_fields.append(f'{section_key} = ?')
                    values.append(content)
            
            update_fields.append('updated_at = ?')
            values.append(now)
            
            values.append(ticker.upper())
            
            sql = f'''
                UPDATE stock_analysis 
                SET {', '.join(update_fields)}
                WHERE ticker = ?
            '''
            cursor.execute(sql, values)
        else:
            cursor.execute('''
                INSERT INTO stock_analysis (
                    ticker, stock_name, chinese_name, exchange,
                    biz, exec, finance, call, ta_price, ta_analyst, ta_social,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker.upper(),
                stock_name,
                chinese_name,
                exchange,
                sections.get('biz', ''),
                sections.get('exec', ''),
                sections.get('finance', ''),
                sections.get('call', ''),
                sections.get('ta_price', ''),
                sections.get('ta_analyst', ''),
                sections.get('ta_social', ''),
                now,
                now
            ))
        
        conn.commit()
        conn.close()

    def update_section(self, ticker: str, section: str, content: str):
        """
        更新特定分析區塊的內容
        
        Args:
            ticker: 股票代碼
            section: 分析區塊名稱
            content: 新的分析內容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        sql = f'''
            UPDATE stock_analysis 
            SET {section} = ?, updated_at = ?
            WHERE ticker = ?
        '''
        
        cursor.execute(sql, (content, now, ticker.upper()))
        conn.commit()
        conn.close()

    def delete_stock(self, ticker: str):
        """刪除股票記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM stock_analysis WHERE ticker = ?',
            (ticker.upper(),)
        )
        
        conn.commit()
        conn.close()

    def get_all_tickers(self) -> list:
        """取得所有已儲存的股票代碼"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT ticker FROM stock_analysis ORDER BY ticker')
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
