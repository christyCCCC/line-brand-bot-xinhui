#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗證 v5：1) reply 失敗自動 push 補送  2) 貼圖回覆"""
import os
os.environ.setdefault('LINE_CHANNEL_SECRET', 't')
os.environ.setdefault('LINE_CHANNEL_ACCESS_TOKEN', 't')
os.environ.setdefault('ADMIN_LINE_USER_ID', 'ADMIN_TEST_ID')

import importlib.util
spec = importlib.util.spec_from_file_location('app', '/home/ubuntu/line-brand-bot/app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

log = []

class FakeProfile:
    def __init__(self, n): self.display_name = n

# 情境一：模擬 reply_message 一律拋錯（reply_token 過期），檢查是否自動 push 補送
class ReplyFailApi:
    def reply_message(self, req):
        raise Exception("400 Invalid reply token")
    def push_message(self, req):
        to = getattr(req, 'to', None)
        for m in req.messages:
            log.append(('PUSH->' + str(to)[:10], getattr(m, 'text', '')[:40]))
    def get_profile(self, u): return FakeProfile('客戶')

# 情境二：reply 正常
class ReplyOkApi:
    def reply_message(self, req):
        for m in req.messages:
            log.append(('REPLY', getattr(m, 'text', '')[:40]))
    def push_message(self, req):
        to = getattr(req, 'to', None)
        for m in req.messages:
            log.append(('PUSH->' + str(to)[:10], getattr(m, 'text', '')[:40]))
    def get_profile(self, u): return FakeProfile('客戶')

class FakeApiClient:
    def __enter__(self): return self
    def __exit__(self, *a): return False

app.chat_with_ai = lambda text, hist: f"[AI回覆]{text}"

class FakeSource:
    def __init__(self, uid): self.type='user'; self.user_id=uid
class FakeTextMsg:
    def __init__(self, t): self.text=t
class FakeTextEvent:
    def __init__(self, uid, t):
        self.source=FakeSource(uid); self.message=FakeTextMsg(t); self.reply_token='tok'
class FakeStickerEvent:
    def __init__(self, uid):
        self.source=FakeSource(uid); self.reply_token='tok'

print("="*60)
print("測試 A：reply 失敗（reply_token 過期）應自動 push 補送")
app.ApiClient = lambda *a,**k: FakeApiClient()
app.MessagingApi = lambda *a,**k: ReplyFailApi()
log.clear()
app.handle_message(FakeTextEvent('user_X', '你好'))
pushed = [x for x in log if x[0].startswith('PUSH->user')]
print("  補送 push 給客戶:", "✅ 成功" if pushed else "❌ 失敗", pushed)

print("="*60)
print("測試 B：貼圖事件應有回覆")
app.MessagingApi = lambda *a,**k: ReplyOkApi()
log.clear()
app.handle_sticker(FakeStickerEvent('user_Y'))
replied = [x for x in log if x[0]=='REPLY']
fwd = [x for x in log if x[0].startswith('PUSH->ADMIN')]
print("  回覆客戶貼圖:", "✅" if replied else "❌", replied)
print("  轉發副本給管理者:", "✅" if fwd else "❌", fwd)

print("="*60)
print("測試 C：貼圖 reply 失敗也要 push 補送")
app.MessagingApi = lambda *a,**k: ReplyFailApi()
log.clear()
app.handle_sticker(FakeStickerEvent('user_Z'))
pushed = [x for x in log if x[0].startswith('PUSH->user')]
print("  貼圖補送 push 給客戶:", "✅" if pushed else "❌", pushed)
print("="*60)
print("完成。")
