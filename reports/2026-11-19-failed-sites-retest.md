# 失敗樣本修復與重測：2026-11-19（Asia/Taipei）

已修復理膚寶水活動頁的正文漏抓，並以最終版本重新連線測試先前未通過的 9 個目標，各跑 HTTP 與 Chromium，共 18 次。**其中理膚寶水改為通過；兩家媒體、五個社群目標與 Reuters 分類頁控制仍有存取限制。**

本輪也重新連線取得全部 22 個目標的結果，再以最終程式重解析保存的 HTML，核對正文與雜訊。一般媒體／品牌的核心區塊通過數由 **13／16 提升為 14／16**：媒體 10／12、品牌 4／4。這是指定樣本的結果，不能推算所有網站的成功率。

## 失敗目標重測結果

| 目標 | 修復前 | 最終 HTTP／Browser 重測 |
|---|---|---|
| [理膚寶水活動頁](https://www.lrp.com.tw/events/sensi2019/index.html) | 163 字符，只剩部分註腳；incomplete_content | 兩模式皆 4,208 字符、無品質警告；TXT 與 Markdown 各命中 138／138 個來源文字片段 |
| [INSIDE](https://www.inside.com.tw/article/42926-ankit-gupta-yc-interview-cs-degree-ai-era) | HTTP 403 | 兩模式仍 403；額外診斷確認 Cloudflare challenge |
| [關鍵評論網](https://www.thenewslens.com/article/271214) | HTTP 403 | 兩模式仍 403；額外診斷確認 Cloudflare challenge |
| Facebook NASA、Nike 帳號入口 | robots_disallowed | 兩模式仍被 robots 規則禁止 |
| Instagram NASA、Nike 帳號入口及一則貼文 | robots_disallowed | 兩模式仍被 robots 規則禁止 |
| Reuters 科技分類頁（控制組） | robots_disallowed | 兩模式仍被 robots 規則禁止；不列入文章通過率 |

上述社群與控制組完整網址保存在 [樣本清單](../examples/extended-sites.json)。兩家媒體的回應包含 `server: cloudflare`、`cf-mitigated: challenge`，頁面標題為驗證等待頁；不是已取得文章後的正文選擇器問題。沒有把驗證頁、預覽摘要或 robots 禁止的網址算成成功。

本輪 Facebook 樣本是兩個帳號入口；Instagram 是兩個帳號入口與一則實際貼文。沒有取得 Facebook 單篇貼文，不能宣稱涵蓋任意社群貼文。現有工具也沒有社群 API 或授權登入功能。

## 修復方式

- 活動頁的教學、問答與產品文案大量使用短 `div／span`，一般正文演算法原本只保留長註腳。新增該排版的內容範圍：hero 與教學區，領試用表單及結果彈窗位於這些範圍之外。
- 將課程標題、問答題目轉為 Markdown 可保留的標題；保留來源中已存在的各分頁、摺疊問答內容，不需要點擊操作。
- 清除點擊提示、領試用按鈕、銷售據點連結與打字動畫片段。圖片文字、影片音訊與尚未下載的內容不包含在這次修復中。
- 短文字完整度比對只用於已識別的活動頁範圍。實測發現，直接套用所有新聞正文容器會把作者推薦及廣告當成漏文，已限縮並加入回歸防護。

這是對已識別排版的適配，沒有宣稱任意活動頁都可完整擷取。品牌文案中的研究數據與功效說法只是原文資料，擷取成功不表示已核實其內容。來源中不同分頁重複的文案仍可能保留。

## 驗證

**101 項測試全數通過，包含 Chromium 整合測試。** Ruff、格式檢查、差異空白檢查與 source distribution／wheel 建置均通過。

另外使用正式 `scrape.cmd` 對理膚寶水跑 browser 模式，退出碼 0、4,208 字符、無品質提示，匯出的 TXT／Markdown 均再次通過 138／138 來源片段比對。

新增的改寫案例覆蓋教學短文字、含行內標籤的句尾、問答、試用彈窗排除，以及一般文章／正文容器不因作者資料而擴大擷取。獨立程式審查對照本輪全部成功取得的 HTML，確認除了理膚寶水之外，最終版本的 TXT、Markdown 與警告皆和修復前版本一致。

來源比對腳本獨立選取原始 HTML 的主要文字，不呼叫產品的正文選取函式。理膚寶水以至少 8 個非空白字符的文字節點驗證，排除註解及指定操作介面；138 個不同片段在兩種輸出皆命中。這不是逐字完整性證明，也不包含圖片中的文字。原有 13 個目標的 225 個區塊維持通過，加上活動頁共 **363／363** 個 browser 來源文字區塊；HTTP 可取得的 12 個目標為 **312／312**。已識別的廣告／推薦字樣沒有洩漏，`regressions` 為空。

原八站另外使用先前保存的 HTML／browser DOM 作回歸；不是本輪重新連線八站。ELLE 15 個商品標題與 33 段、Vogue 20 個商品標題與 50 段、Cosmopolitan 128 個圖庫文字區塊，在 TXT、Markdown 均維持保留。

完整重現指令（公開網站回應可能改變）：

```powershell
.\.venv\Scripts\python.exe -m pytest --run-browser -q --tb=short --basetemp=.cache/campaign-release-final-tests
# 101 passed in 27.13s
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode http --phase repaired
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode browser --phase repaired
.\.venv\Scripts\python.exe scripts/verify_extended_sites.py --phase repaired
```

等兩種模式全部完成，再執行來源比對。benchmark 完成不代表所有網址成功；JSON 中仍保留受阻結果。

## 本機證據

資料夾時間使用 UTC。完整文章與 HTML 都留在忽略目錄，GitHub 只保存程式、改寫測試、來源清單與摘要。

- 全部 22 目標網路原始輸出：`output/extended-sites/repaired/http/20261119T132510Z_c7431c6f/`、`output/extended-sites/repaired/browser/20261119T132557Z_7695178d/`。
- 最終版本重解析：`output/extended-sites/repaired/http/20261119T132828Z_ef93d3d6/`、`output/extended-sites/repaired/browser/20261119T132834Z_7e000513/`；比對結果 `output/extended-sites/repaired/verification.json`。
- 最終版本失敗目標連線重試：`output/extended-sites/failed-final/http/20261119T132929Z_d8e5ece7/`、`output/extended-sites/failed-final/browser/20261119T132932Z_91d9cf35/`；比對結果 `output/extended-sites/failed-final/verification.json`。
- 原八站保存 HTML 回歸：`output/campaign-regression/verification.json`。
- 正式 CLI 最終連線測試：`output/lrp-cli-final/20261119T133148Z_c3f72bce/`。
- 403 診斷：`.cache/failed-access-diagnostics.json`；robots 原文保存於 `.cache/www.facebook.com-robots.txt`、`.cache/www.instagram.com-robots.txt`、`.cache/www.reuters.com-robots.txt`。

未通過的存取限制仍然存在；這次修復解決的是可取得 HTML 的活動頁正文漏抓。
