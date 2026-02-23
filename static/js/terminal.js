/* ================================================================
   terminal.js - 分析終端 JavaScript
   ================================================================
   適用於：index.html（主分析頁面）
   
   依賴：
     - 頁面需有 data-ticker 屬性在 <body> 或主容器上
     - DOM 元素 ID 規則：dot-{id}, preview-{id}, btn-{id},
                         update-{id}, badge-{id}
   
   函數索引：
     1. fetchSection()    — 呼叫 API 取得分析報告
     2. updateSection()   — 強制重新分析
     3. openPopUp()       — 開啟彈出報告視窗
     4. toggleMinimize()  — 視窗最小化切換
     5. toggleMaximize()  — 視窗最大化切換
     6. startDrag()       — 視窗拖曳系統
   ================================================================ */


/* ==========================================================
   全域變數
   ========================================================== */
let analysisCache = {};    // 儲存各模組的 HTML 報告內容

// 從 <body data-ticker="NVDA"> 讀取股票代碼
const TICKER = document.body.dataset.ticker || '';


/* ==========================================================
   頁面載入：自動觸發全部 7 個分析模組
   ========================================================== */
window.onload = function () {
    const sections = ['biz', 'finance', 'exec', 'call', 'ta_price', 'ta_analyst', 'ta_social'];
    sections.forEach(id => fetchSection(id));
};


/* ==========================================================
   1. fetchSection - 呼叫後端 API 取得分析報告
   ----------------------------------------------------------
   參數：
     sectionId   (str)  : 分析模組 ID，如 'biz', 'finance'
     forceUpdate (bool) : 是否強制重新生成（略過快取）
   
   流程：
     1. 顯示載入動畫（金色脈衝）
     2. POST /analyze/<sectionId>
     3. 成功 → 預覽文字 + 「開啟報告」+ 「重新分析」
     4. 失敗 → 錯誤訊息 + 紅色指示燈
   ========================================================== */
async function fetchSection(sectionId, forceUpdate = false) {
    const dot       = document.getElementById(`dot-${sectionId}`);
    const preview   = document.getElementById(`preview-${sectionId}`);
    const btn       = document.getElementById(`btn-${sectionId}`);
    const updateBtn = document.getElementById(`update-${sectionId}`);
    const badge     = document.getElementById(`badge-${sectionId}`);

    // 載入狀態
    dot.className = 'loading-pulse';
    preview.innerHTML = '正在計算核心數據並生成報告...';
    if (badge) badge.innerHTML = '';
    if (updateBtn) updateBtn.disabled = true;

    try {
        const response = await fetch(`/analyze/${sectionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: TICKER, force_update: forceUpdate })
        });
        const data = await response.json();

        if (data.success) {
            // ✅ 成功
            analysisCache[sectionId] = data.report;

            const temp = document.createElement('div');
            temp.innerHTML = data.report;
            preview.innerText = temp.innerText.substring(0, 80) + '...';
            preview.classList.remove('italic', 'text-gray-400');
            preview.classList.add('text-gray-600');

            dot.className = 'w-2 h-2 rotate-45 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]';
            btn.classList.remove('hidden');

            if (updateBtn) {
                updateBtn.style.display = 'block';
                updateBtn.disabled = false;
            }

            // 快取標記
            if (badge) {
                if (data.from_cache && !forceUpdate) {
                    badge.innerHTML = '<span class="cache-badge cached">非即時數據</span>';
                } else {
                    badge.innerHTML = '<span class="cache-badge fresh">FRESH</span>';
                    setTimeout(() => { badge.innerHTML = ''; }, 3000);
                }
            }
        } else {
            // ❌ 失敗
            preview.innerHTML = data.error || '分析失敗，請重試';
            dot.className = 'w-2 h-2 rotate-45 bg-red-500';
            if (updateBtn) updateBtn.disabled = false;
        }
    } catch (e) {
        preview.innerHTML = '數據連結中斷，請重試';
        dot.className = 'w-2 h-2 rotate-45 bg-red-500';
        if (updateBtn) updateBtn.disabled = false;
    }
}


/* ==========================================================
   2. updateSection - 強制重新分析
   ========================================================== */
async function updateSection(sectionId) {
    if (!confirm('確定要重新分析此區塊嗎？\n\n⚠️ 這將呼叫 AI API 生成最新分析。')) return;

    const updateBtn = document.getElementById(`update-${sectionId}`);
    const originalText = updateBtn.textContent;
    updateBtn.textContent = '更新中...';
    updateBtn.disabled = true;

    await fetchSection(sectionId, true);

    updateBtn.textContent = '✅ 已更新';
    setTimeout(() => { updateBtn.textContent = originalText; }, 2000);
}


/* ==========================================================
   3. openPopUp - 開啟彈出報告視窗
   ========================================================== */
function openPopUp(id, title) {
    // 同一模組視窗已存在則先關閉
    const existing = document.getElementById(`win-${id}`);
    if (existing) existing.remove();

    const win = document.createElement('div');
    win.id = `win-${id}`;
    win.className = 'draggable-window';
    win.style.top = '7.5vh';
    win.style.left = '7.5vw';

    win.innerHTML = `
        <div class="window-header" onmousedown="startDrag(event, 'win-${id}')">
            <div class="window-header-left">
                <div class="window-header-icon"></div>
                <span class="window-header-title">${title}</span>
                <span class="window-header-tag">// ${TICKER} 智能終端</span>
            </div>
            <div class="window-controls">
                <button class="window-ctrl-btn btn-minimize" onclick="toggleMinimize('win-${id}')" title="最小化">
                    <svg viewBox="0 0 16 16"><line x1="3" y1="8" x2="13" y2="8"/></svg>
                </button>
                <div class="window-ctrl-divider"></div>
                <button class="window-ctrl-btn btn-maximize" onclick="toggleMaximize('win-${id}')" title="最大化">
                    <svg viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" rx="1"/></svg>
                </button>
                <div class="window-ctrl-divider"></div>
                <button class="window-ctrl-btn btn-close" onclick="document.getElementById('win-${id}').remove()" title="關閉">
                    <svg viewBox="0 0 16 16"><line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/></svg>
                </button>
            </div>
        </div>
        <div class="window-body">
            <div class="max-w-4xl mx-auto py-4">
                ${analysisCache[id] || '<p style="color:#999;">暫無數據</p>'}
            </div>
        </div>`;

    document.getElementById('popup-container').appendChild(win);
}


/* ==========================================================
   4. toggleMinimize - 最小化切換
   ========================================================== */
function toggleMinimize(winId) {
    const win = document.getElementById(winId);
    if (!win) return;
    if (win.classList.contains('maximized')) win.classList.remove('maximized');
    win.classList.toggle('minimized');

    const minBtn = win.querySelector('.btn-minimize svg');
    if (win.classList.contains('minimized')) {
        minBtn.innerHTML = '<polyline points="3 11 8 6 13 11"/>';
    } else {
        minBtn.innerHTML = '<line x1="3" y1="8" x2="13" y2="8"/>';
    }
}


/* ==========================================================
   5. toggleMaximize - 最大化切換
   ----------------------------------------------------------
   關鍵：用 inline style 覆蓋 CSS 的 max-width: 1200px
   ========================================================== */
function toggleMaximize(winId) {
    const win = document.getElementById(winId);
    if (!win) return;

    if (win.classList.contains('minimized')) {
        win.classList.remove('minimized');
        win.querySelector('.btn-minimize svg').innerHTML = '<line x1="3" y1="8" x2="13" y2="8"/>';
    }

    const isMaximized = win.classList.toggle('maximized');

    if (isMaximized) {
        win.dataset.prevTop = win.style.top;
        win.dataset.prevLeft = win.style.left;
        win.style.top = '0px';
        win.style.left = '0px';
        win.style.width = '100vw';
        win.style.height = '100vh';
        win.style.maxWidth = '100vw';
        win.style.borderRadius = '0';
    } else {
        win.style.top = win.dataset.prevTop || '7.5vh';
        win.style.left = win.dataset.prevLeft || '7.5vw';
        win.style.width = '';
        win.style.height = '';
        win.style.maxWidth = '';
        win.style.borderRadius = '';
    }

    const maxBtn = win.querySelector('.btn-maximize svg');
    if (isMaximized) {
        maxBtn.innerHTML = '<rect x="4.5" y="1.5" width="10" height="10" rx="1"/><rect x="1.5" y="4.5" width="10" height="10" rx="1"/>';
    } else {
        maxBtn.innerHTML = '<rect x="2.5" y="2.5" width="11" height="11" rx="1"/>';
    }
}


/* ==========================================================
   6. 拖曳系統（requestAnimationFrame 高效能）
   ========================================================== */
let dragObj = null, offX = 0, offY = 0, rafId = null, lastX = 0, lastY = 0;

function startDrag(e, id) {
    if (e.target.closest('.window-controls')) return;
    const win = document.getElementById(id);
    if (win.classList.contains('maximized') || win.classList.contains('minimized')) return;

    dragObj = win;
    document.querySelectorAll('.draggable-window').forEach(w => w.style.zIndex = 1000);
    dragObj.style.zIndex = 1001;
    dragObj.style.willChange = 'left, top';
    offX = e.clientX - dragObj.offsetLeft;
    offY = e.clientY - dragObj.offsetTop;

    document.onmousemove = (ev) => {
        ev.preventDefault();
        lastX = ev.clientX;
        lastY = ev.clientY;
        if (!rafId) rafId = requestAnimationFrame(updateDrag);
    };
    document.onmouseup = () => {
        if (dragObj) dragObj.style.willChange = 'auto';
        dragObj = null;
        rafId = null;
        document.onmousemove = null;
        document.onmouseup = null;
    };
}

function updateDrag() {
    if (dragObj) {
        dragObj.style.left = (lastX - offX) + 'px';
        dragObj.style.top = (lastY - offY) + 'px';
    }
    rafId = null;
}
