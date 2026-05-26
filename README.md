# LINE AI 品牌建構師「心惠」

鏡水方舟品牌靈魂提煉系統 - LINE Bot 版本

## 功能

- 根據三種 TA（企業主/個人品牌/創業者）引導品牌框架問答
- 整合 OpenAI GPT 進行品牌分析
- 產出品牌人格、品牌故事、命名方向、行銷策略建議

## 環境變數

| 變數名稱 | 說明 |
|---------|------|
| LINE_CHANNEL_SECRET | LINE Messaging API Channel Secret |
| LINE_CHANNEL_ACCESS_TOKEN | LINE Messaging API Channel Access Token |
| OPENAI_API_KEY | OpenAI API Key |
| OPENAI_API_BASE | OpenAI API Base URL (選填) |

## 部署到 Render

1. Fork 此 repo
2. 在 Render 建立新的 Web Service
3. 連接 GitHub repo
4. 設定環境變數
5. 部署完成後，將 Webhook URL 設定到 LINE Developers Console

## 本地開發

```bash
pip install -r requirements.txt
python app.py
```
