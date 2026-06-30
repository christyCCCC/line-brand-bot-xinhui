# IG 自動發佈設定指南（Meta Graph API）

要讓系統自動把圖文發佈到您的 Instagram，必須透過官方的 **Meta Graph API**。以下是完整的條件與設定步驟。

---

## 前置條件（缺一不可）

| 條件 | 說明 |
|------|------|
| 1. IG 商業/創作者帳號 | 個人帳號無法用 API 發佈，需在 IG App 設定中切換為「商業帳號」 |
| 2. Facebook 粉絲專頁 | IG 商業帳號必須綁定一個 FB 粉專 |
| 3. Meta for Developers App | 在 developers.facebook.com 建立一個 App |
| 4. 長期 Access Token | 取得不會過期（或可刷新）的存取權杖 |
| 5. IG Business Account ID | 您的 IG 商業帳號的數字 ID |

---

## 設定步驟

### Step 1：將 IG 切換為商業帳號
1. 打開 Instagram App → 設定 → 帳號
2. 選擇「切換為專業帳號」→ 選「商業」
3. 綁定您的 Facebook 粉絲專頁（沒有的話需先建立一個）

### Step 2：建立 Meta App
1. 前往 https://developers.facebook.com
2. 用您的 FB 帳號登入 → 我的應用程式 → 建立應用程式
3. 類型選「商業」
4. 新增產品：Instagram Graph API、Facebook Login

### Step 3：取得 Access Token
1. 在 Graph API Explorer 中產生使用者權杖
2. 需要的權限（scope）：
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
3. 將短期 Token 換成長期 Token（60 天，可程式化刷新）

### Step 4：取得 IG Business Account ID
透過 API 查詢：
```
GET /me/accounts → 取得 FB Page ID
GET /{page-id}?fields=instagram_business_account → 取得 IG Business Account ID
```

---

## 發佈流程（系統自動執行）

IG 圖片發佈是「兩步驟」：

1. **建立媒體容器**
   ```
   POST /{ig-user-id}/media
   參數：image_url（公開圖片網址）, caption（文案）
   → 回傳 creation_id
   ```

2. **發佈容器**
   ```
   POST /{ig-user-id}/media_publish
   參數：creation_id
   → 回傳貼文 ID，即發佈成功
   ```

3. **取得貼文連結**
   ```
   GET /{media-id}?fields=permalink
   → 回傳 IG 貼文網址（用於 LINE 導流）
   ```

---

## 需要您提供 / 操作的事項

**最簡單的方式**：您可以接管瀏覽器，我引導您一步步完成 Meta App 建立與授權，最後把 Access Token 與 IG Business Account ID 設定到系統。

或者，如果您已經有現成的：
- Meta App 與長期 Access Token
- IG Business Account ID

直接提供給我，我就能完成串接。

---

## 替代方案（若不想設定 Meta API）

如果 Meta API 設定太複雜，可採用**半自動**：
1. 系統自動生成圖片 + 文案
2. 傳到您的 LINE / 後台讓您確認
3. 您手動發到 IG（複製文案、上傳圖片）
4. 您把 IG 貼文連結貼回，系統自動在 LINE 發送導流訊息

這個方式不需要任何 Meta 授權，但每篇需要您手動發佈 IG。
