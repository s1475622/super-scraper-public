# 媒體與美妝爬蟲修復驗證：2026-11-19（Asia/Taipei）

已修復原先三篇商品清單的大量漏抓，並修復驗證時發現的正文誤刪與瀏覽器動態推薦污染。完整測試 **71 項通過**，含 Chromium 整合測試；八站各一篇，以 HTTP／browser 各執行一次，最後一輪 **16/16 成功，無品質提示**。

這次將「抓到文字」與「指定內容確實保留」分開驗證。原始基準與漏抓證據保留在 [修復前報告](2026-11-19-media-beauty-test.md)，沒有覆蓋原始輸出。

## 八站修復前後

字符數為正文的非空白 Unicode 字符數，包含標點；不是詞數，也不是完整性分數。

| 網站／樣本 | 修復前 | 修復後 HTTP | 修復後 Browser | 驗證結果 |
|---|---:|---:|---:|---|
| [中央社](https://www.cna.com.tw/news/afe/202609070189.aspx) | 684 | 684 | 684 | 原有 6 個主要段落均保留。 |
| [聯合新聞網](https://udn.com/news/story/7326/9848865) | 937 | 910 | 910 | 原有 7 個主要段落均保留；27 字符標題不再重複放入正文，仍在 title 欄位。 |
| [自由時報](https://news.ltn.com.tw/news/life/breakingnews/5643993) | 997 | 997 | 997 | 原有 8 個主要段落均保留。 |
| [ELLE](https://www.elle.com/tw/beauty/skin/g42401973/2026-moisture-lotion/) | 466 | 3,290 | 3,290 | **15/15 商品標題、33/33 商品段落保留**，標題順序正確。 |
| [Vogue](https://www.vogue.com.tw/beauty/article/%E7%B2%BE%E8%8F%AF%E6%B6%B2%E6%8E%A8%E8%96%A6) | 3,775 | 4,620 | 4,620 | **20/20 編號商品標題、50/50 正文段落保留**，包含三段圖片中的產品說明，標題順序正確。 |
| [BEAUTY美人圈](https://www.beauty321.com/post/71017) | 9,665 | 11,529 | 11,529 | 抽查商品清單、正文與 Q&A；開頭段落比對通過，清除 Taboola 動態推薦。 |
| [Marie Claire](https://www.marieclaire.com.tw/beauty/skin-care/95897) | 4,383 | 4,759 | 4,759 | 抽查趨勢段落與 Q&A；開頭段落比對通過，移除延伸閱讀列表。 |
| [Cosmopolitan](https://www.cosmopolitan.com/tw/beauty/skin/a70152193/2026-cosmo-clean-beauty-awards-winner-list/) | 1,519 | 5,701 | 5,701 | **128/128 圖庫文字區塊保留**，涵蓋得獎產品、評審介紹與評語。 |

上列內容命中檢查同時對純文字 `text` 與 `markdown` 執行，HTTP／browser 兩種模式均通過。三個新聞樣本的「主要段落」指修復前輸出中至少 40 個非空白字符的段落；不包含較短標題。BEAUTY 與 Marie Claire 是抽查，未宣稱逐段證明整篇完整。

## 根因與修復

- ELLE 圖文清單、Cosmopolitan 嵌入圖庫原本就在 HTML 中，但正文演算法把它們當成雜訊。現在先辨識主要文章中的正文區塊，檢查重要段落與標題是否被保留，必要時以原結構輸出文字與 Markdown。
- Vogue 的編號標題使用 `div role="heading"`，先轉成真正標題再擷取；多段正文依 DOM 順序組合，排除父子區塊重複。明確標記的圖片編輯文字也會保留，攝影署名分開清理。
- 獨立審查重現了三種回歸風險：側欄的 `.article-body` 取代真正文章、嵌套正文外的導言／結語漏掉、含 APP 連結的正文整段被刪。已各補回歸案例並修復，APP／社群清理只移除連結與明確的獨立促銷文案。
- 實際 browser 測試發現 ELLE／Cosmopolitan 會插入推薦輪播，BEAUTY 會插入 Taboola。已保存渲染後 HTML、重現污染並修復；最終輸出沒有本次已識別的推薦輪播、Taboola、Watch Next 與社群加入提示。
- 新增 `incomplete_content` 品質提示：已識別的正文區塊若在最終輸出仍有主要段落或標題缺失，會明確標示。

沒有按網站網域選擇不同爬蟲；使用正文、標題與推薦元件的結構標記。登入／付費／驗證限制仍沿用原行為。

## 自動與實測驗證

```powershell
.\.venv\Scripts\python.exe -m pytest --run-browser -q --tb=short --basetemp=.cache/content-final-confirmed
# 71 passed in 25.93s

.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
uv lock --check --offline
uv build --offline --quiet
```

上述檢查均通過。新增 22 項正文回歸案例，以改寫的小型 HTML 測試圖文清單、嵌入圖庫、ARIA 標題、表格、父子重複、側欄、導言結語、APP／社群、編輯圖片說明與動態推薦；測試資料不複製整篇公開文章。

實際抓取與比對：

```powershell
.\scrape.cmd --file examples/media-beauty-urls.txt --mode http --timeout 15 --retries 0 --delay 1 --output output/media-beauty-repaired/http
.\scrape.cmd --file examples/media-beauty-urls.txt --mode browser --timeout 20 --wait-ms 2000 --retries 0 --delay 1 --output output/media-beauty-repaired/browser
.\.venv\Scripts\python.exe scripts/verify_media_beauty.py
```

比對腳本直接從保存的原始 HTML 獨立列出商品標題與文字區塊，不呼叫產品的正文選擇函式；忽略空白、Markdown 強調／跳脫符號，以及圖庫的 `See more details` 操作提示。另檢查商品標題順序、主要新聞段落保留與已知推薦雜訊。最後一輪 `failures` 為空陣列。

本機檔案（執行資料夾使用 UTC）：

- HTTP：`output/media-beauty-repaired/http/20261118T175416Z_eebdb3a1/articles.json`
- Browser：`output/media-beauty-repaired/browser/20261118T175437Z_721750d9/articles.json`
- 量化比對：`output/media-beauty-repaired/verification.json`
- 每次執行另有 CSV、逐篇 TXT 與 Markdown。
- 原始 HTML：`.cache/media-beauty-html/1.html` 至 `8.html`；三站的動態 DOM 為 `4-browser.html`、`6-browser.html`、`8-browser.html`。

HTML 與完整文章匯出只保存在本機，未納入版本控制；重現比對腳本需要這些檔案。原始與修復過程中的執行結果均保留。

## 實際限制

這八篇樣本通過指定內容檢查，不代表所有網站與所有文章都保證完整。檢查只涵蓋已下載、已識別的正文與主要段落；未載入內容、短段落、未知排版仍可能漏掉。一般照片說明不保證保留，署名、圖片來源與免責聲明仍可能出現在正文。

HTTP 與 browser 的字符數相同，但字串不必完全一致：瀏覽器渲染可能移動圖片品牌署名或改變空白。比對通過條件為指定文字保留及商品標題順序，而非兩份文字逐字相等。

本次修復聚焦正文；作者來源可能仍是網站 metadata，發表日期仍採明示的 `datePublished`／published meta，與更新日期不同，沒有改成猜測記者或以更新時間覆蓋發表日期。
