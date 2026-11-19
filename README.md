# Super Scraper

輸入一個或一批文章網址，擷取正文與文章資訊，匯出 JSON、CSV、TXT 和 Markdown，方便後續分析。支援中文與其他語言，本機執行，不需要 API Key。

本工具結合 **HTTP／Playwright、Trafilatura 與 BeautifulSoup／markdownify 備援**。預設直接下載 HTML；需要執行 JavaScript 時，明確選用瀏覽器模式。

**擷取成功只代表取得文字，不代表已證明文章完整。** 登入提示、付費牆、摘要、延遲載入或特殊排版可能影響結果；分析前請檢查品質提示，並抽查原文。

## 開始使用（Windows / PowerShell）

完成下方安裝步驟後，在專案資料夾執行：

```powershell
# 單篇文章：請換成實際網址
.\scrape.cmd "https://example.com/article"

# 一次多篇
.\scrape.cmd "https://example.com/article-a" "https://example.com/article-b"

# 每行一個網址的 UTF-8 檔案
.\scrape.cmd --file .\examples\urls.txt

# 正文需要 JavaScript 才會出現
.\scrape.cmd --file .\examples\urls.txt --mode browser
```

`examples/urls.txt` 內的網址是示範用，請先換成要分析的文章。包含 `&`、`?` 的網址也請加引號。

不使用啟動腳本也可以：

```powershell
.\.venv\Scripts\python.exe -m super_scraper "https://example.com/article"
.\.venv\Scripts\super-scraper.exe --file urls.txt --output output
```

## 在另一台電腦安裝

需要 Python 3.11 以上與 Git。Windows 專案若位於中文路徑，請使用本次已驗證的 Python 3.13，避免 Python 3.11 載入套件路徑時的編碼問題。以下 uv 指令固定使用 Python 3.13：

```powershell
git clone https://github.com/s1475622/super-scraper-public.git
cd super-scraper-public
uv sync --frozen --python 3.13
```

需要瀏覽器模式時：

```powershell
uv sync --frozen --extra browser --python 3.13
.\.venv\Scripts\python.exe -m playwright install chromium
```

也可在新的 Python 虛擬環境使用 pip：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# 瀏覽器模式改裝：
.\.venv\Scripts\python.exe -m pip install -e ".[browser]"
.\.venv\Scripts\python.exe -m playwright install chromium
```

macOS / Linux 可使用 `.venv/bin/python -m super_scraper`；本次開發與實測環境為 Windows、Python 3.13。

## 輸入與選項

網址檔每行一個完整 `http://` 或 `https://` 網址，允許 UTF-8 BOM、空行，以及以 `#` 開頭的註解。可以同時提供命令列網址與 `--file`。工具保留輸入順序、去除相同網址與 fragment 重複，但保留 query string。

```text
# urls.txt
https://example.com/article-a
https://example.com/article-b?lang=zh
```

不會探索首頁、分類頁、站內連結或 sitemap；不會自動登入。

| 選項 | 預設 | 用途 |
|---|---|---|
| `--file` | 無 | UTF-8 網址清單 |
| `--output` | `output` | 匯出根目錄 |
| `--mode` | `http` | `http` 或 `browser` |
| `--timeout` | `20` | 每次網路操作的逾時秒數 |
| `--delay` | `1` | 不同輸入網址間的等待秒數 |
| `--retries` | `2` | 暫時失敗的額外重試次數，可設 0–5 |
| `--max-bytes` | `10485760` | HTML 大小上限，預設 10 MiB |
| `--wait-ms` | `2000` | browser 載入後額外等待毫秒，可設 0–10000 |
| `--help` | — | 顯示完整說明 |

HTTP 429、500、502、503、504 及暫時性網路錯誤可重試，HTTP 404 等永久失敗不重試。HTTP 重新導向最多 10 次。重試退避最多等 5 秒；HTTP 模式會參考數字型 `Retry-After`。重試、轉址、robots 查詢及瀏覽器等待會增加總耗時，`--timeout` 不是整批工作期限。

工具快取 robots.txt 並遵守明確禁止規則，包含重新導向後的主要文件；無法取得 robots 時，仍繼續執行並留下 `robots_unavailable` 提示。

## 匯出結果

每次建立獨立資料夾，資料夾名稱使用 UTC 時間及隨機識別碼，不覆蓋上次結果：

```text
output/
  20261119T010000Z_a1b2c3d4/
    articles.json
    articles.csv
    text/
      0001_網址雜湊.txt
    markdown/
      0001_網址雜湊.md
```

- `articles.json`：UTF-8、保留中文，包含每個網址的成功或失敗紀錄。
- `articles.csv`：UTF-8 BOM，可用 Excel 開啟；品質提示以分號分隔。可能被 Excel 當成公式的字串會加上單引號前綴，原始值保留在 JSON。
- `text/*.txt`：每篇獨立的純文字，附標題、來源與品質提示。
- `markdown/*.md`：同篇的 Markdown 版本。

文章檔案名稱採序號與網址雜湊，不以網頁標題當路徑，避免 Windows 非法字元與同名覆寫。失敗項目僅出現在 JSON／CSV。

| 欄位 | 意義 |
|---|---|
| `url` / `final_url` | 輸入網址／最後取得文件的網址 |
| `canonical_url` | 網頁明確宣告的 canonical URL，若有 |
| `title`, `author`, `published_date` | 擷取到的標題、作者、發表日期 |
| `site_name`, `language` | 網頁宣告的網站名稱與 HTML 語言 |
| `text`, `markdown` | 正文與 Markdown |
| `char_count` | 正文的非空白 Unicode 字符數，包含標點；不是中文詞數 |
| `extracted_at` | UTC ISO 8601 擷取時間 |
| `mode`, `status` | 抓取模式、`success` 或 `error` |
| `warnings`, `error` | 品質提示、失敗原因 |

未知資訊使用 JSON `null`／CSV 空欄。日期只接受網頁明示的發表時間（meta、JSON-LD `datePublished` 或標記為發表時間的 time 元素），目前解析 ISO 日期；不從網址或內文猜測。擷取結果並非經過人工核實。

## 品質提示與限制

| 提示 | 建議處理 |
|---|---|
| `short_content` | 正文不足 100 個非空白字符，檢查是否只是摘要或短文。 |
| `incomplete_content` | 已識別的正文區塊仍有段落或標題未保留；先對照原文，避免直接進入分析。 |
| `fallback_extraction` | 正文演算法未取得內容，改用 HTML 區塊備援，請特別抽查雜訊。 |
| `possible_access_wall` | 文字出現登入、訂閱或驗證相關訊息，可能不是可分析的完整文章。 |
| `try_browser_mode` | HTTP 內容偏短，可嘗試 `--mode browser`，再比較原文。 |
| `robots_unavailable` | 無法取得可解析的 robots.txt；這不是網站已允許抓取的證據。 |

此版**不會把 OpenGraph／meta description 預覽摘要重建成正文**。登入、付費或驗證頁的文字仍可能被擷取並附提示；偵測屬於啟發式，無法涵蓋所有網站。

擷取時會辨識文章正文、圖文清單、多段正文與嵌入商品圖庫，將 `role="heading"` 轉成標題，並比對主要段落是否被正文演算法漏掉；發現缺漏時，改從已識別的正文區塊保留文字與 Markdown。正文範圍以主要文章為優先，避免誤選側欄，同時保留放在正文容器外的導言與結語。商品圖片中明確標記的編輯文字也會保留；一般照片說明不保證保留。

完整度檢查主要比對至少 40 個非空白字符的段落、至少 4 個字符的標題，以及明確標記的編輯圖片說明；不是逐字完整性證明。已識別的活動頁教學範本另檢查至少 12 個字符的短 div／span／清單文案。無法辨識正文範圍時，也會檢查是否有多個實際文字片段缺漏並提出警告，不會直接把整頁當正文。相關閱讀、明確廣告及部分社群推廣會清理，但來源說明、署名或免責聲明仍可能留下。

支援多段正文、粗體換行的問答標題，以及以 `div` 標示的正文段落。遇到無限捲動載入多篇文章時，會在網頁有宣告文章 URL 的情況下，依輸入網址／canonical 選擇對應文章，避免合併其他篇。

針對理膚寶水測試活動頁，已加入範本適配：保留教學、問答及產品文案，排除領試用彈窗、導覽與操作提示。這是已識別排版的支援，其他活動頁仍需驗證。

Facebook／Instagram 目前不承諾貼文擷取。2026-11-19 重測的四個公開帳號入口與一則 Instagram 貼文，皆被 robots 規則禁止；使用 browser 模式也不會繞過這項限制。INSIDE 與關鍵評論網仍回傳 Cloudflare 驗證頁（403）。媒體與品牌樣本最新為 14／16 個核心區塊比對通過，見 [失敗樣本修復重測](reports/2026-11-19-failed-sites-retest.md)；先前結果見 [擴大網站驗證](reports/2026-11-19-expanded-sites-verification.md)。

瀏覽器模式使用乾淨、非持久的 Chromium context，各篇分開；不讀取你的 Chrome 個人資料，也不自動捲動或點擊「顯示更多」。主要 HTML 文件在渲染前透過 CDP 串流分段讀取並限制解壓後大小，也會檢查渲染後 HTML。這不是網頁所有圖片、影片與其他資源的流量配額。

這是單機命令列工具，沒有雲端服務、LLM 分析、排程、代理池或驗證碼處理。中途按 Ctrl+C 會終止，本次尚未完成的批次不會匯出；已完成的其他執行資料夾不受影響。

## 退出碼

| 退出碼 | 狀態 |
|---|---|
| `0` | 每篇都取得內容，仍可能有品質提示 |
| `1` | 有單篇失敗，其餘結果已匯出 |
| `2` | 整體輸入、設定、依賴或輸出發生問題 |
| `130` | 使用者中止 |

## 開發與驗證

```powershell
uv sync --frozen --all-extras --python 3.13
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest --run-browser -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

測試使用本機 HTTP 伺服器與中英文 HTML，不依賴外部網站穩定性。瀏覽器測試預設略過，使用 `--run-browser` 才執行。

八個媒體／美妝網站的真實樣本結果與重現方式，見 [修復驗證報告](reports/2026-11-19-media-beauty-repair-verification.md)。`scripts/verify_media_beauty.py` 可對照本機保存的原始 HTML 與兩種模式的匯出結果；需要報告所列的本機資料，不會另外下載網站內容。

擴大實測包含 12 家媒體文章、4 個品牌頁、5 個社群目標，以及一個分類頁控制。擷取器與驗證腳本分開執行，保存原 HTML 以便核對；網路結果會隨時間與地區改變，不列為離線單元測試的通過條件：

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode http --phase repaired
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode browser --phase repaired
.\.venv\Scripts\python.exe scripts/verify_extended_sites.py --phase repaired
```

請依序執行並等兩種模式完成，再進行比對。這組 benchmark 完成不代表所有網站都成功；最後的 JSON 會區分正文比對通過、內容不完整、存取受阻與其他失敗。範例與來源選擇器位於 `examples/extended-sites.json`，直接使用 CLI 可改讀 `examples/extended-sites-urls.txt`。完整文章與 HTML 都留在忽略的 `output/`、`.cache/` 目錄，不會上傳 GitHub。

## 來源

正文擷取使用 Trafilatura，並以 BeautifulSoup／markdownify 保留已識別正文中的段落、標題與 Markdown。

- [Trafilatura 文件](https://trafilatura.readthedocs.io/en/latest/usage-python.html)
- [Playwright Python 文件](https://playwright.dev/python/docs/library)
- [設計](docs/superpowers/specs/2026-11-19-article-scraper-design.md)
- [實作計畫](docs/superpowers/plans/2026-11-19-article-scraper.md)
