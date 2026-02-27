import json
import os
import glob

# JSON files live in the stock_code/ subfolder alongside this script
_STOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_code")

def _load_lookup() -> dict:
    files = sorted(glob.glob(os.path.join(_STOCK_DIR, "stock_code_*.json")))
    path = files[-1] if files else os.path.join(_STOCK_DIR, "stock_code.json")
    with open(path, encoding="utf-8") as f:
        print(f"[stock_lookup] Loaded: {os.path.basename(path)}")
        return json.load(f)

_lookup = _load_lookup()


def normalize_ticker(ticker: str) -> str:
    raw = ticker.upper().strip()
    if '.' in raw or not raw.isdigit():
        return raw
    return raw.zfill(4) + '.HK' if len(raw) <= 4 else raw


def _find(ticker: str) -> dict | None:
    """Return the raw JSON entry for a ticker, or None."""
    code = normalize_ticker(ticker)
    base = code.split('.')[0]
    for key in [code, base] + [base.zfill(n) for n in (4, 5, 6)]:
        if key in _lookup:
            return _lookup[key]
    return None


def get_stock_info(ticker: str) -> tuple[str, str] | tuple[None, None]:
    """Return (name, exchange) for use by app.py, or (None, None) if not found."""
    entry = _find(ticker)
    if entry:
        return entry["name"], entry["exchange"]
    return None, None


def get_name(ticker: str) -> str:
    """Return formatted name + exchange for CLI display."""
    entry = _find(ticker)
    if entry:
        return f"{entry['name']}  [{entry['exchange']}]"
    return f"Not found: {ticker}"


if __name__ == "__main__":
    print(f"Loaded {len(_lookup):,} entries from {_STOCK_DIR}")
    print("Type 'q' to quit.\n")
    while True:
        code = input("Stock code: ").strip()
        if code.lower() in ("q", "quit", "exit"):
            break
        if code:
            print(f"  → {get_name(code)}\n")
