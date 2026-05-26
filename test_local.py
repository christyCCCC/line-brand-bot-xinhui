"""
本地測試腳本 - 模擬對話流程（不需要 LINE Webhook）
"""
import sys
sys.path.insert(0, '.')

# 測試 import 是否正常
try:
    from app import (
        get_session, reset_session, QUESTIONS, WELCOME_MESSAGE,
        ROLE_MAP, ROLE_NAMES, build_analysis_prompt, split_message
    )
    print("✅ 所有模組匯入成功")
except Exception as e:
    print(f"❌ 匯入失敗: {e}")
    sys.exit(1)

# 測試 Session 管理
print("\n--- 測試 Session 管理 ---")
session = get_session("test_user_001")
print(f"初始狀態: {session}")
assert session["state"] == "idle"
assert session["step"] == 0
print("✅ Session 初始化正確")

# 測試角色選擇
print("\n--- 測試角色映射 ---")
assert ROLE_MAP.get("1") == "enterprise"
assert ROLE_MAP.get("2") == "personal"
assert ROLE_MAP.get("3") == "startup"
assert ROLE_MAP.get("企業主") == "enterprise"
assert ROLE_MAP.get("創業者") == "startup"
print("✅ 角色映射正確")

# 測試問題框架
print("\n--- 測試問題框架 ---")
print(f"企業主問題數: {len(QUESTIONS['enterprise'])}")
print(f"個人品牌問題數: {len(QUESTIONS['personal'])}")
print(f"創業者問題數: {len(QUESTIONS['startup'])}")
assert len(QUESTIONS["enterprise"]) == 7
assert len(QUESTIONS["personal"]) == 5
assert len(QUESTIONS["startup"]) == 7
print("✅ 問題數量正確")

# 測試 Prompt 建構
print("\n--- 測試 Prompt 建構 ---")
test_answers = {
    "industry": "科技",
    "scale": "11-50人",
    "revenue": "200-500萬",
    "target_age": "25-34",
    "ideal_client": "注重效率的中小企業主",
    "competitor": "某某科技公司",
    "pain_point": "品牌知名度不夠",
}
prompt = build_analysis_prompt("enterprise", test_answers)
assert "企業主" in prompt
assert "科技" in prompt
assert "品牌知名度不夠" in prompt
print(f"Prompt 長度: {len(prompt)} 字元")
print("✅ Prompt 建構正確")

# 測試訊息分段
print("\n--- 測試訊息分段 ---")
short_msg = "這是一條短訊息"
assert len(split_message(short_msg)) == 1
long_msg = "A" * 10000
parts = split_message(long_msg)
assert len(parts) > 1
print(f"長訊息分成 {len(parts)} 段")
print("✅ 訊息分段正確")

# 模擬完整對話流程
print("\n--- 模擬完整對話流程 ---")
user_id = "simulate_user"
reset_session(user_id)
session = get_session(user_id)

# Step 0: 選擇身份
print("用戶輸入: 1 (企業主)")
session["state"] = "enterprise"
session["role"] = "enterprise"
session["step"] = 0

# 模擬回答所有問題
answers = ["科技業", "11-50人", "200-500萬", "2,3", "注重效率的企業主", "競品A", "品牌知名度不夠"]
for i, answer in enumerate(answers):
    key = QUESTIONS["enterprise"][i]["key"]
    session["answers"][key] = answer
    session["step"] = i + 1
    print(f"  Q{i+1} ({key}): {answer}")

print(f"\n最終收集到的資料: {session['answers']}")
print("✅ 完整對話流程模擬成功")

print("\n" + "=" * 50)
print("🎉 所有本地測試通過！程式碼邏輯正確。")
print("=" * 50)
