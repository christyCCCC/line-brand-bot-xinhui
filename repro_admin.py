#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重現：管理者本人傳訊息時，Bot 是否會回覆。"""
import os, traceback
os.environ.setdefault('LINE_CHANNEL_SECRET', 't')
os.environ.setdefault('LINE_CHANNEL_ACCESS_TOKEN', 't')
os.environ.setdefault('ADMIN_LINE_USER_ID', 'Uc2223fdd64bb3fbd06f17977dbee5830')

import importlib.util
spec = importlib.util.spec_from_file_location('app', '/home/ubuntu/line-brand-bot/app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

events_log = []

class FakeProfile:
    def __init__(self, name): self.display_name = name

class FakeMessagingApi:
    def reply_message(self, req):
        for m in req.messages:
            events_log.append(('REPLY', getattr(m, 'text', str(m))))
    def push_message(self, req):
        to = getattr(req, 'to', None)
        for m in req.messages:
            events_log.append(('PUSH->' + str(to)[:8], getattr(m, 'text', str(m))))
    def get_profile(self, user_id):
        return FakeProfile('管理者本人')

class FakeApiClient:
    def __enter__(self): return self
    def __exit__(self, *a): return False

app.ApiClient = lambda *a, **k: FakeApiClient()
app.MessagingApi = lambda *a, **k: FakeMessagingApi()
# 用真實 chat_with_ai？這裡改用 stub 以隔離 AI，先確認流程有沒有走到回覆
app.chat_with_ai = lambda text, hist: f"[AI回覆] 針對「{text}」"

class FakeSource:
    def __init__(self, uid):
        self.type = 'user'
        self.user_id = uid

class FakeMessage:
    def __init__(self, text): self.text = text

class FakeEvent:
    def __init__(self, uid, text):
        self.source = FakeSource(uid)
        self.message = FakeMessage(text)
        self.reply_token = 'fake-token'

ADMIN = 'Uc2223fdd64bb3fbd06f17977dbee5830'
for t in ['Hi', '你好', '在嗎']:
    events_log.clear()
    try:
        app.handle_message(FakeEvent(ADMIN, t))
        print(f"\n=== 管理者傳「{t}」===")
        if not events_log:
            print("  ⚠️ 沒有任何回覆或推播（就是已讀不回的狀況！）")
        for kind, txt in events_log:
            print(f"  [{kind}] {txt[:60]}")
    except Exception as e:
        print(f"\n=== 管理者傳「{t}」發生例外 ===")
        traceback.print_exc()
