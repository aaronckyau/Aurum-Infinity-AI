# 🏛️ Aurum Intelligence — AI 股票分析終端

> 基於 Google Gemini API 的多維度股票分析平台，支援美股、港股、A 股

## ✨ 功能

| 模組 | 分析內容 |
|------|---------|
| 📊 商業模式 | 價值主張、業務拆解、競爭格局、護城河評分 |
| 💰 財務質量 | GAAP vs Non-GAAP、非經常性項目、紅旗偵測 |
| 👔 管理層評估 | 高管背景、內部交易、誠信記錄 |
| 🎙️ 法說會解構 | Guidance、管理層語氣、隱藏風險信號 |
| 📈 價格技術 | 趨勢判斷、支撐壓力、技術指標 |
| 🎯 期權籌碼 | Put/Call Ratio、Max Pain、Gamma 敞口 |
| 💬 社群情緒 | 散戶情緒、媒體基調、產品口碑 |

## 🚀 快速開始

```bash
# 1. 複製專案
git clone https://github.com/你的帳號/stock-analysis.git
cd stock-analysis

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 設定 API Key
cp .env.example .env
# 編輯 .env，填入你的 API Key

# 4. 啟動
python app.py

# 5. 打開瀏覽器
# http://127.0.0.1:5000
```

## 📁 專案結構

```
Stock_analysis/
├── app.py                  # Flask 後端主程式
├── prompt_manager.py       # Prompt 模板管理器
├── prompts/
│   └── prompts.yaml        # 所有 AI Prompt 模板
├── templates/
│   ├── base.html           # 共用模板（品牌色、字體）
│   ├── index.html          # 主分析頁面
│   └── error.html          # 錯誤頁面
├── .env.example            # 環境變數範例
├── .gitignore              # Git 忽略清單
└── requirements.txt        # Python 依賴
```

## ⚙️ 環境變數

| 變數 | 說明 | 取得方式 |
|------|------|---------|
| `GEMINI_API_KEY` | Google Gemini API Key | [Google AI Studio](https://aistudio.google.com/apikey) |
| `FMP_API_KEY` | Financial Modeling Prep API Key | [FMP Developer](https://financialmodelingprep.com/developer) |

## ⚠️ 免責聲明

本平台由 AI 生成的分析僅供參考，不構成投資建議。詳見頁面底部完整免責聲明。

## 📄 License

Private — 僅限內部使用
