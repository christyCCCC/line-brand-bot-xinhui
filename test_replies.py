#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模擬 LINE 文字訊息事件，測試 Bot 對各種輸入的回覆。"""
import os
os.environ.setdefault('LINE_CHANNEL_SECRET', 't')
os.environ.setdefault('LINE_CHANNEL_ACCESS_TOKEN', 't')
os.environ.setdefault('ADMIN_LINE_USER_ID', 'ADMIN_TEST_ID')

import importlib.util
spec = importlib.util.spec_from_file_location('app', '/home/ubuntu/line-brand-bot/app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

# 捕捉所有送出的回覆
sent = []

class FakeProfile:
    def __init__(self, name):
        self.display_name = name

class FakeMessagingApi:
    def reply_message(self, req):
        for m in req.messages:
            sent.append(getattr(m, 'text', str(m)))
    def push_message(self, req):
        to = getattr(req, 'to', None)
        prefix = '[FWD->ADMIN] ' if to == 'ADMIN_TEST_ID' else '[PUSH] '
        for m in req.messages:
            sent.append(prefix + getattr(m, 'text', str(m)))
    def get_profile(self, user_id):
        return FakeProfile('測試客戶')

class FakeApiClient:
    def __enter__(self): return self
    def __exit__(self, *a): return False

# 替換掉真實的 LINE API client
app.ApiClient = lambda *a, **k: FakeApiClient()
app.MessagingApi = lambda *a, **k: FakeMessagingApi()

# 攔截 AI 聊天，避免真的呼叫 OpenAI（測試流程用 stub）
app.chat_with_ai = lambda text, hist: f"[AI回覆] 針對「{text}」的智能回應內容…"

# 重置 session 儲存
class FakeSource:
    def __init__(self, uid):
        self.type = 'user'
        self.user_id = uid

class FakeMessage:
    def __init__(self, text):
        self.text = text

class FakeEvent:
    def __init__(self, uid, text):
        self.source = FakeSource(uid)
        self.message = FakeMessage(text)
        self.reply_token = 'fake-token'

def run(uid, text, label):
    sent.clear()
    app.handle_message(FakeEvent(uid, text))
    print(f"\n{'='*60}")
    print(f"【{label}】客戶輸入：{text!r}")
    print('-'*60)
    for s in sent:
        print(s)

# 測試 1：全新客戶輸入 05
run('user_A', '05', '測試1：輸入 05（海外品牌拓展）')
# 測試 2：同一客戶接著回 B（在 service_flow 狀態）
run('user_A', 'B', '測試2：05 之後回覆 B')
# 測試 3：另一客戶輸入 01
run('user_B', '01', '測試3：輸入 01（品牌方向探索）')
# 測試 4：打招呼
run('user_C', '你好', '測試4：打招呼「你好」')
# 測試 5：隨意問題
run('user_D', '請問你們收費多少？', '測試5：任意問題（價格）')
# 測試 6：服務選單關鍵字
run('user_E', '你們有什麼服務', '測試6：服務選單關鍵字')
# 測試 7：預約
run('user_F', '我要預約', '測試7：預約')
# 測試 8：隨便亂打
run('user_G', 'asdfgh', '測試 8：隨便亂打字')
# 測試 9：問 IG
run('user_H', 'ig', '測試 9：只打 ig')
# 測試 10：問 IG（句子）
run('user_I', '你們有 instagram 嗎', '測試 10：你們有 instagram 嗎')
# 測試 11：半形 5
run('user_J', '5', '測試 11：只打半形 5')
# 測試 12：全形５
run('user_K', '５', '測試 12：只打全形 ５')

print(f"\n{'='*60}")
print("全部測試完成。")
