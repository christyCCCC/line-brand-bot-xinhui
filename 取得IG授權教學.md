# 取得 Instagram 自動發佈授權教學

> 目標：取得兩個關鍵資訊 —— **IG_BUSINESS_ACCOUNT_ID** 與 **IG_ACCESS_TOKEN**，填入 Render 環境變數後，系統就能自動把圖文發佈到您的 IG（@brand_0214sh）。

---

## 前置條件確認

| 項目 | 您的狀態 | 說明 |
|------|----------|------|
| IG 帳號類型 | ✅ 數位創作者 | 創作者/商業帳號都可用 API |
| 綁定 FB 粉專 | ⚠️ 待確認 | **這是 Meta API 的硬性要求** |
| Meta 開發者帳號 | ⚠️ 待建立 | 免費註冊 |

**重點：Instagram 自動發佈一定要透過「Facebook 粉絲專頁」中介，IG 必須先綁定一個 FB 粉專。**

---

## 第一步：確認 / 建立 Facebook 粉絲專頁並綁定 IG

1. 到 Facebook，建立一個粉絲專頁（如果還沒有），名稱可用「心惠品牌靈魂建構所」
2. 打開手機 **Instagram App** → 個人檔案 → 右上角選單 → **設定與隱私**
3. 進入 **帳號類型與工具** → **分享至其他應用程式** 或 **連結的帳號**
4. 連結到剛才建立的 **Facebook 粉絲專頁**

> 完成後，您的 IG 就和一個 FB 粉專綁定了。

---

## 第二步：建立 Meta 開發者 App

1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 用您的 Facebook 帳號登入 → 右上角 **我的應用程式** → **建立應用程式**
3. 應用程式類型選 **「商業」(Business)**
4. 填入應用程式名稱（例如：心惠IG自動發佈）→ 建立

---

## 第三步：取得 Access Token（使用 Graph API Explorer）

1. 前往 [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. 右上角「Meta App」選擇您剛建立的 App
3. 點 **「Generate Access Token」**，授權時勾選以下權限：
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
4. 產生後會得到一段 **短期 Access Token**（先複製起來）

---

## 第四步：取得 IG Business Account ID

在 Graph API Explorer 中，依序查詢（把網址貼到上方查詢列，按送出）：

1. 查您的粉專 ID：
   ```
   me/accounts
   ```
   → 找到您的粉專，記下它的 `id`（粉專 ID）

2. 用粉專 ID 查 IG 帳號 ID：
   ```
   {粉專ID}?fields=instagram_business_account
   ```
   → 回傳的 `instagram_business_account.id` 就是 **IG_BUSINESS_ACCOUNT_ID**

---

## 第五步：把短期 Token 換成長期 Token（重要！）

短期 Token 只有 1 小時，必須換成 60 天的長期 Token。

把以下網址的參數換成您的資料，貼到瀏覽器執行：

```
https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={App_ID}&client_secret={App_Secret}&fb_exchange_token={短期Token}
```

- `App_ID`、`App_Secret`：在 Meta App 的「設定 → 基本資料」中
- 回傳的 `access_token` 就是 **60 天長期 Token**

> 提示：之後我可以幫您設定「自動續期」，讓 Token 永不過期。

---

## 第六步：把資訊交給我

完成後，請把以下兩個值貼給我（或自行填入 Render 環境變數）：

```
IG_BUSINESS_ACCOUNT_ID = （第四步取得的數字 ID）
IG_ACCESS_TOKEN = （第五步取得的長期 Token）
```

我會幫您填入 Render，並立即測試自動發佈。

---

## 如果覺得設定太複雜？

沒關係，我們可以先用**半自動模式**：
1. 系統自動生成圖片 + 文案
2. 我把圖文傳給您，您手動發到 IG（30 秒）
3. 您把 IG 連結貼回給我
4. 系統自動在 LINE 發送導流訊息給 5,755 位粉絲

兩種模式的程式我都已經寫好，您隨時可以切換。
