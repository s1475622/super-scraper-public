# 修復圖文清單漏抓與完整度判斷

使用者已授權：跑測試、驗證，發現問題直接修復。這是既有擷取器的缺陷修復，延續原已核准的單篇／批次 CLI 設計。

## 根因與修正方向

已保存的真實 HTML 證明內容在文件裡：ELLE 使用 listicle-slides／data-journey-body，Cosmopolitan 使用 embedded-gallery-grid，Vogue 使用 role=heading 的 div 與多個 body__inner-container。Trafilatura 的正文清理會丟棄這些區塊；更換瀏覽器不能修復。

優先使用可靠的正文語意標記與獨立片段，保留原順序、段落、列表和 role=heading，避免按網域寫死規則。一般文章繼續使用既有 Trafilatura 路徑。若已識別的內容區塊在最終結果仍有缺漏，輸出明確品質提示。移除明確的相關閱讀、推薦、廣告與末尾雜訊，避免改成全頁擷取。

## 任務與驗證

- [x] 以真實 DOM 結構製作小型、改寫文字的離線 fixtures；先重現 listicle／嵌入商品圖庫／ARIA 標題缺漏及缺漏無警告。
- [x] 修正正文區塊選擇、語意轉換與結構完整度檢查，驗證引言、首尾商品、標題、評語與順序；確認排除導覽、廣告、相關推薦，避免誤採側欄。
- [x] 重跑舊測試與實際 8 站的 HTTP／browser 擷取，以原 HTML 的商品標題、段落與首尾區塊比對；保留修復前輸出。
- [x] 進行一次獨立程式審查，對重要問題補回歸測試並修復；更新 README 與實測報告，留下實際檢查結果。

## 檔案範圍

新增專注於正文語意的模組 `src/super_scraper/content.py`（若有必要拆分），修改 `extractor.py`，新增 `tests/test_content.py` 與小型 fixtures，更新品質提示說明及報告。保留現有抓取、robots、CLI 與匯出契約。

## 審查重點

不能只靠字符數挑最長文字；不得混入側欄推薦。多個正文片段必須維持 DOM 順序，不重複輸出父子區塊。ARIA 標題必須在 TXT 和 Markdown 都保留。品質提示要檢查實際缺漏，不應因無關頁面導覽產生假警告。未知網站仍須保留舊路徑。

## 進度

根因已從三站的公開 HTML 定位。工作在目前 codex/article-scraper 分支的原工作目錄繼續，不建立額外 worktree 或修改原來源 repo。

已完成一次獨立審查並修復三項重要發現（側欄誤選、容器外段落遺失、促銷連結誤刪整段正文）。額外實測發現編輯圖片說明漏抓及動態推薦污染，均先重現、補回歸測試再修復。完整測試 71 項通過，八站兩種模式最後一輪 16/16 成功；獨立 HTML／匯出比對無失敗。詳見 `reports/2026-11-19-media-beauty-repair-verification.md`。
