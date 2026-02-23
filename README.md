# 🏛️ Aurum Infinity — AI 股票分析终端

> 基于 Google Gemini API 的多维度股票分析平台，支持美股、港股、A 股

---

## ✨ 功能模块

| 模块 | 分析内容 |
|------|----------|
| 📊 商业模式 | 价值主张、业务拆解、竞争格局、护城河评分 |
| 👔 治理效能 | 高管背景、内部交易、诚信记录 |
| 💰 财务质量 | GAAP vs Non-GAAP、非经常性项目、红旗侦测 |
| 🎙️ 会议展望 | Guidance、管理层语气、隐藏风险信号 |
| 📈 价格行为 | 趋势判断、支撑压力、技术指标 |
| 🎯 市场预测 | 分析师评级、目标价、机构整体看法 |
| 💬 社区情绪 | 散户情绪、媒体基调、网上讨论热度 |

---

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/aaronckyau/Aurum-Infinity-AI.git
cd Aurum-Infinity-AI

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 启动服务
python app.py

# 5. 打开浏览器
# http://127.0.0.1:5000
```

---

## 📁 项目结构

```
Aurum-Infinity-AI/
├── app.py               # Flask 后端主程序
├── prompt_manager.py    # Prompt 模板管理器
├── prompts/
│   └── prompts.yaml     # 所有 AI Prompt 模板
├── templates/
│   ├── base.html        # 共用模板（品牌色、字体）
│   ├── index.html       # 主分析页面
│   └── error.html       # 错误页面
├── .env.example         # 环境变量范例
├── .gitignore           # Git 忽略清单
└── requirements.txt     # Python 依赖列表
```

---

## ⚙️ 环境变量

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `GEMINI_API_KEY` | Google Gemini API 密钥 | [Google AI Studio](https://aistudio.google.com/) |
| `FMP_API_KEY` | Financial Modeling Prep API 密钥 | [FMP Developer](https://financialmodelingprep.com/developer) |

---

## ⚠️ 免责声明

本平台由 AI 生成的分析内容仅供参考，不构成任何投资建议。详见页面底部完整免责声明。

---

## 📄 License

Private — 仅限内部使用
