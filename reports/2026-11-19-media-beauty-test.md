# 媒體與美妝網站實測：2026-11-19（Asia/Taipei）

## 結果

測試 8 個網站，每站選 1 篇公開文章，分別執行 HTTP 與 Chromium browser 模式，共 16 次擷取。兩種模式的 8 組純正文輸出均完全相同。

程式對 16 次擷取皆回報 success，且沒有品質警告；但人工抽查與原始 HTML 對照後，**3 篇有重大漏抓，不能當作完整文章分析**。這次測試沒有更改產品程式，也沒有以診斷結果覆蓋原始輸出。

字符數依工具定義，為正文的非空白 Unicode 字符數，包含標點。下表兩種模式字符數相同。

| 類別 | 網站與測試文章 | HTTP 字符數 | Browser 字符數 | 正文品質判定 |
|---|---|---:|---:|---|
| 媒體 | [中央社：藥妝零售營業額](https://www.cna.com.tw/news/afe/202609070189.aspx) | 684 | 684 | 抽查正常；新聞正文與末段編輯資訊可讀。 |
| 媒體 | [聯合新聞網：台灣咖啡節](https://udn.com/news/story/7326/9848865) | 937 | 937 | 抽查正常；多段新聞正文與結尾活動說明可讀。 |
| 媒體 | [自由時報：叫車平台納管](https://news.ltn.com.tw/news/life/breakingnews/5643993) | 997 | 997 | 抽查正常；正文段落可讀，含一段圖片說明。 |
| 美妝 | [ELLE：15款保濕化妝水](https://www.elle.com/tw/beauty/skin/g42401973/2026-moisture-lotion/) | 466 | 466 | **不完整**；只有引言、Q&A，15 個商品介紹段落漏抓，尾端含 Watch Next。 |
| 美妝 | [Vogue：20款精華液](https://www.vogue.com.tw/beauty/article/%E7%B2%BE%E8%8F%AF%E6%B6%B2%E6%8E%A8%E8%96%A6) | 3,775 | 3,775 | **不完整**；保留多數產品描述、價格，20 個編號商品標題全部未保留，另有若干內文段落缺漏。 |
| 美妝 | [BEAUTY美人圈：保濕精華液清單](https://www.beauty321.com/post/71017) | 9,665 | 9,665 | 正文可讀，保留商品內容與末尾 Q&A；也保留圖片來源和延伸閱讀，分析前應清理。 |
| 美妝 | [Marie Claire：抗老保養趨勢](https://www.marieclaire.com.tw/beauty/skin-care/95897) | 4,383 | 4,383 | 正文可讀，含趨勢段落與末尾 Q&A；仍混入延伸閱讀及免責聲明。 |
| 美妝 | [Cosmopolitan：純淨美妝大賞](https://www.cosmopolitan.com/tw/beauty/skin/a70152193/2026-cosmo-clean-beauty-awards-winner-list/) | 1,519 | 1,519 | **不完整**；保留目錄、類別標題與工作人員名單，大量得獎商品與評審評語漏抓。 |

「抽查正常／正文可讀」是針對這次樣本的判定，不代表已逐字證明完整，更不代表同站所有文章都能成功。

## 重大漏抓的證據

- ELLE 原始 HTML 有 15 個「保濕化妝水推薦」商品標題及介紹段落，輸出的商品標題命中數為 0/15。原始 HTML 已含這些內容，不是單純等待 JavaScript 就能補回。
- Vogue 原始 HTML 的 strong 區塊有 20 個編號商品名稱；去掉編號並忽略空白後，完整商品名稱在擷取正文的命中數仍為 0/20。原文中的多數價格和描述卻有保留，會造成商品與描述難以對應。
- Cosmopolitan 原始 HTML 具有得獎產品和評審評語；現行輸出未保留抽查的 BIODERMA、CLARINS 商品與相關評語，卻保留許多目錄和製作名單內容。
- 三篇缺漏樣本的 warnings 都是空陣列；現有的「不足 100 字符」檢查無法發現這類重大缺漏。

## 只讀診斷

另以原始 HTML 比較 Trafilatura 設定，未更動正式程式：

| 樣本 | favor_precision（目前） | 一般設定 | favor_recall |
|---|---:|---:|---:|
| ELLE | 466 | 466 | 466 |
| Vogue | 3,775 | 3,978 | 3,978 |
| Cosmopolitan | 1,519 | 5,227 | 5,227 |

Cosmopolitan 在非 precision 設定下能補回抽查的商品內容，但這不等於已驗證整篇完整；ELLE 單換這些設定仍無效。依「原始 HTML 已有內容、兩種抓取模式輸出一致」的證據，問題主要在正文區塊辨識與清理，而不是沒有取得網頁。

後續修正應針對圖文商品清單、商品標題與正文區塊保留，並增加結構完整度警告；不應只把字符數超過門檻當作分析可用的依據。

## 日期與作者的附帶觀察

ELLE 和 Vogue 的輸出發表日期較早，與頁面顯示的 2026 年時間不同。原始 metadata 分別明確宣告了早期 article:published_time 與 2026 年 article:modified_time；目前欄位只保存發表日期，沒有保存更新日期，不能直接把日期差異判成抓取錯誤。聯合與自由的作者欄位也可能是網站名稱，而非記者署名；本次表格的判定只針對正文品質。

## 重現方式

網址清單：`examples/media-beauty-urls.txt`。

```powershell
.\scrape.cmd --file examples/media-beauty-urls.txt --mode http --timeout 15 --retries 0 --delay 1 --output output/media-beauty/http
.\scrape.cmd --file examples/media-beauty-urls.txt --mode browser --timeout 20 --wait-ms 2000 --retries 0 --delay 1 --output output/media-beauty/browser
```

本次原始輸出（執行資料夾名稱為 UTC）：

- HTTP：`output/media-beauty/http/20261118T172328Z_eaaef889/articles.json`
- Browser：`output/media-beauty/browser/20261118T172346Z_64cabd9f/articles.json`
- 各資料夾也保留 CSV、每篇獨立 TXT 與 Markdown。
- 三個問題樣本的原始 HTML 與設定比較存於 `.cache/media-beauty-html/`，供後續修正使用，未納入版本控制。
