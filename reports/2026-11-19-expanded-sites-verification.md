# 擴大網站正文驗證：2026-11-19（Asia/Taipei）

後續已修復理膚寶水活動頁並重測失敗目標，最新結果為 14／16 篇媒體與品牌樣本通過，見 [失敗樣本修復重測](2026-11-19-failed-sites-retest.md)。以下保留本輪原始結果。

本輪新增 **22 個目標**：12 家媒體文章、4 個品牌頁、4 個公開社群帳號入口、1 則實際 Instagram 貼文，以及 1 個 Reuters 分類頁控制。各以 HTTP／Chromium browser 實測，共 44 次抓取；另重跑原有八站。

依兩種模式中較佳的結果，**一般媒體／品牌共 13/16 篇通過指定核心正文比對**。這是所選樣本的命中結果，不能推論所有網站的成功率。

| 類別 | 核心正文通過 | 不完整 | 存取受阻 |
|---|---:|---:|---:|
| 新增媒體文章 | 10/12 | 0 | 2 |
| 品牌內容頁 | 3/4 | 1 | 0（Dyson 需 browser） |
| FB／IG 公開目標 | 0/5 | 0 | 5 |
| Reuters 分類頁控制 | 不計文章分母 | — | 1 |

HTTP 的 22 個目標：11 個核心正文通過、1 個不完整、10 個受阻。Browser：13 個通過、1 個不完整、8 個受阻。`success` 只代表產出文字，不直接當作正文通過。

## 媒體逐站結果

字符數為正文的非空白 Unicode 字符數，包含標點。來源區塊比對同時對 TXT 與 Markdown 執行，並檢查已識別的介面與推薦雜訊。

| 媒體與來源 | HTTP 字符數／限制 | Browser 字符數／限制 | 核心來源區塊保留 |
|---|---:|---:|---|
| [ETtoday](https://www.ettoday.net/news/20261119/3275171.htm) | 295 | 295 | 3/3 |
| [公視新聞](https://news.pts.org.tw/article/759090) | 577 | 577 | 8/8 |
| [報導者](https://www.twreporter.org/a/2026-taipei-golden-horse-film-festival-chairmanship-hands-over) | 6,547 | 6,547 | 43/43 |
| [INSIDE](https://www.inside.com.tw/article/42926-ankit-gupta-yc-interview-cs-degree-ai-era) | HTTP 403 | HTTP 403 | 未取得正文 |
| [科技新報](https://technews.tw/2026/11/19/intel-18a-process-major-breakthrough-first-external-customer/) | 502 | 502 | 5/5 |
| [泛科學](https://pansci.asia/archives/382531) | 2,242 | 2,242 | 13/13 |
| [TVBS](https://news.tvbs.com.tw/life/4053157) | 788 | 788 | 5/5 |
| [三立新聞](https://www.setn.com/news/1941795) | 557 | 557 | 5/5 |
| [天下雜誌](https://www.cw.com.tw/article/5143757) | HTTP 403 | 3,133 | 31/31 |
| [BBC 中文](https://www.bbc.com/zhongwen/articles/c38x04eppnpdo/trad) | 2,468 | 2,468 | 26/26 |
| [The Guardian](https://www.theguardian.com/science/2026/nov/19/ipcc-report-delay-climate-crisis-scientist) | 6,457 | 6,457 | 23/23 |
| [關鍵評論網](https://www.thenewslens.com/article/271214) | HTTP 403 | HTTP 403 | 未取得正文 |

天下的 browser 取得指定核心段落，但 robots.txt 未能取得可解析政策，因此仍保留 `robots_unavailable`；這不是已獲網站許可的證據。INSIDE、關鍵評論網兩種模式都回應 403，沒有將錯誤頁當成正文。

## 品牌逐站結果

| 品牌與來源 | HTTP 字符數／限制 | Browser 字符數／限制 | 核心來源區塊保留 |
|---|---:|---:|---|
| [Apple](https://www.apple.com/tw/newsroom/2025/09/apple-introduces-iphone-17/) | 6,125 | 5,720 | 24/24 |
| [Nike](https://about.nike.com/en/newsroom/releases/what-is-nike-tuned-air) | 4,767 | 4,767 | 19/19 |
| [Dyson](https://www.dyson.tw/haircare/hairscience7.aspx) | HTTP 403 | 2,090 | 20/20 |
| [理膚寶水](https://www.lrp.com.tw/events/sensi2019/index.html) | 163 | 163 | 未取得正文 |

**理膚寶水未通過**：163 字符主要是部分研究註解，主要課程文字沒有取得，現在會輸出 `incomplete_content`。活動頁缺少明確文章結構，短 div／span、桌機／手機內容與活動介面交錯；沒有為了增加成功數而把整頁介面當成正文。

Apple 的 24/24 區塊、Nike 的 19/19 段與 Dyson 的 20/20 主要文字片段均通過；Apple 兩模式的圖片說明不同。Dyson 仍包含購買／服務資訊。

## 社群與控制樣本

| 目標與來源 | 頁面種類 | HTTP／Browser 結果 |
|---|---|---|
| [Facebook NASA](https://www.facebook.com/NASA/) | 公開帳號入口 | 均為 robots_disallowed |
| [Facebook Nike](https://www.facebook.com/nike/) | 公開帳號入口 | 均為 robots_disallowed |
| [Instagram NASA](https://www.instagram.com/nasa/) | 公開帳號入口 | 均為 robots_disallowed |
| [Instagram Nike](https://www.instagram.com/nike/) | 公開帳號入口 | 均為 robots_disallowed |
| [Instagram 公開貼文（報導者內嵌來源）](https://www.instagram.com/p/DfhSfHbmR23/) | 公開貼文 | 均為 robots_disallowed |
| [Reuters 分類頁存取控制](https://www.reuters.com/technology/) | 分類頁控制 | 均為 robots_disallowed |

Instagram 貼文網址取自報導者原文的內嵌連結。上述網址在主要文件取得前即被 robots 檢查擋下，沒有讀取個人登入資料。Facebook 貼文正文尚未取得、IG 實際貼文也未取得，不能宣稱支援任意公開社群貼文。這是本輪網址與環境的觀察，不是對所有地區與網址的永久判定。

社群資料來源需要另外規劃權限：[Instagram API with Instagram Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login) 面向企業／創作者專業帳號；[Facebook Pages API](https://developers.facebook.com/documentation/pages-api/posts) 需要 token、權限，其他公開粉專資料另受審核功能限制。不等於可取得任意個人帳號貼文，本輪沒有實作或宣稱完成 API 串接。

## 修復內容

- 報導者原本只取得 492 字符的內嵌年表；現在保留包住 widget 的完整正文，並限制在該正文範圍，避免擴大到兄弟文章。
- 清除 TVBS／三立的推薦新聞、科技新報贊助與電子報介面，以及動態的第三方廣告、影片播放器及品牌延伸文章。正文變短時，以來源段落確認沒有誤刪主文。
- 無限捲動頁面根據宣告的文章 URL 與輸入網址／canonical 選取對應文章，避免泛科學的其他篇一起被輸出。
- 保留粗體換行問答標題及明確以 div 標記的段落；Nike 補回四個問答標題，Apple 補回兩段正文。
- 無可信正文範圍但有多個實際文字片段缺漏時，提出不完整提示；理膚寶水不再以空警告呈現。
- 清理 CDP 回呼生命週期，避免關閉的廣告子框架產生未處理例外；主文件攔截錯誤仍保留，包含取得 HTML 時才派發的錯誤。

獨立審查重現「正文擴大至兄弟文章」與「取得 HTML 後的主文件錯誤未檢查」，均先加入失敗回歸測試再修復。最後的 Glia 影片廣告清理使用同一份保存 HTML 重跑所有已成功取得的頁面，保留原始抓取時間與輸出，不把重解析寫成新的網路抓取。另以最終版本重新從網路測試泛科學、TVBS、Nike，37/37 個來源區塊仍保留，沒有已識別的廣告／推薦字樣。

## 驗證與重現

**95 項測試全數通過**，含 Chromium 整合測試。Ruff、格式、鎖定檔與套件建置均通過。原八站重新抓取皆成功，最終程式對八站保存 HTML 的回歸亦通過：ELLE 15 個商品標題、Vogue 20 個商品標題、Cosmopolitan 128 個圖庫文字區塊維持保留。

新增樣本的 browser 模式中，13 個通過目標合計 **225/225 個來源區塊**在 TXT 與 Markdown 均命中。來源選擇器獨立保存在 `examples/extended-sites.json`；比對腳本不呼叫產品的正文選擇函式，忽略空白、Markdown 強調／跳脫符號及 sup/sub 格式。

```powershell
.\.venv\Scripts\python.exe -m pytest --run-browser -q --tb=short --basetemp=.cache/expanded-release-tests
# 95 passed in 28.41s
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode http --phase final
.\.venv\Scripts\python.exe scripts/benchmark_sites.py --mode browser --phase final
.\.venv\Scripts\python.exe scripts/verify_extended_sites.py --phase final
```

依序等兩種模式完成再比對；網路內容與存取政策可能改變。本次 `regressions` 為空，代表指定區塊與限制提示的檢查通過，**不代表所有目標皆取得完整正文**。

本機證據（資料夾使用 UTC）：

- 網路原始輸出：`output/extended-sites/final/http/20261119T130832Z_2ed5a980/`、`output/extended-sites/final/browser/20261119T130912Z_cdae98c7/`。
- 最終重解析輸出：`output/extended-sites/final/http/20261119T131210Z_48e6adb7/`、`output/extended-sites/final/browser/20261119T131217Z_1b8334d4/`。
- 比對結果：`output/extended-sites/final/verification.json`。
- 原 HTML／動態 DOM：`.cache/extended-sites/final/http/`、`.cache/extended-sites/final/browser/`。
- 三站最終網路 smoke：`output/extended-sites/postfix-browser-smoke/20261119T131311Z_30710fba/`。
- 原八站新擷取：`output/media-beauty-repaired/http/20261119T130304Z_5e337965/`、`output/media-beauty-repaired/browser/20261119T130324Z_738bd2d0/`。

完整文章、HTML、快取與本機環境均被 `.gitignore` 排除；repository 只保存程式、來源網址、改寫的測試案例、腳本與摘要報告。

## 能力限制

一般媒體與品牌頁可持續擴大支援；browser 本輪改善了天下與 Dyson 的存取，但兩家媒體仍 403，一篇品牌活動頁仍不完整。核心區塊通過不是逐字完整性證明，署名、照片說明、參考資料、產品標籤或服務資訊仍可能保留，未知排版與尚未載入的內容仍需要抽查。FB／IG 的授權資料來源應作為獨立工作，不宜只增加 HTML 選擇器就宣稱通用支援。
