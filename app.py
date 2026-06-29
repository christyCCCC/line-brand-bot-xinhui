"""
LINE AI 品牌建構師「心惠」- 主程式
心惠｜品牌靈魂建構所 Hui Brand Lab
含預約諮詢系統
"""

import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Flask, request, abort, render_template, jsonify

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent, JoinEvent
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    BroadcastRequest,
    TextMessage,
)

from openai import OpenAI

# ===== 設定 =====
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LINE API 設定
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# OpenAI 設定
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# Email 設定
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "christy.com.tw@gmail.com")

# LINE 通知設定 - 管理者的 LINE User ID
ADMIN_LINE_USER_ID = os.environ.get("ADMIN_LINE_USER_ID", "")

# LINE SDK 設定
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ===== 預約資料儲存 =====
bookings = []

# ===== 已知用戶 user_id 儲存（用於 Push Message 替代 Broadcast）=====
KNOWN_USERS_FILE = "/tmp/known_users.json"

def load_known_users():
    """從檔案載入已知用戶列表"""
    try:
        if os.path.exists(KNOWN_USERS_FILE):
            with open(KNOWN_USERS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading known users: {e}")
    return []

def save_known_user(user_id):
    """記錄新的 user_id（如果尚未記錄）"""
    try:
        users = load_known_users()
        if user_id and user_id not in users:
            users.append(user_id)
            with open(KNOWN_USERS_FILE, "w") as f:
                json.dump(users, f)
            logger.info(f"New user recorded: {user_id} (total: {len(users)})") 
    except Exception as e:
        logger.error(f"Error saving known user: {e}")

# ===== 心惠的系統人設 =====
SYSTEM_PROMPT = """你是「心惠」，品牌靈魂建構所（Hui Brand Lab）的 AI 品牌顧問。

【你的身份】
- 你代表的品牌：心惠｜品牌靈魂建構所（Hui Brand Lab），延伸自鏡水方舟品牌策略系統
- 你的角色：AI 品牌顧問助理、品牌探索引導者、品牌策略夥伴、創業陪跑助手
- 你的使命：讓品牌被理解、被記住、被選擇

【你的語氣與風格】
- 專業但有溫度，偏高端品牌顧問感，不會太冰冷
- 初次對話使用「您」，熟悉後可轉「你」
- 偶爾使用 ✨💡📈 等表情符號，但不過度可愛化，維持高端感
- 不使用過多驚嘆號，不用太活潑的網路用語
- 回答簡潔有力，不囉嗦

【你的口頭禪/金句（適時自然融入對話）】
- 真正的問題，通常不在表面。
- 品牌不是只有好看。
- 找到品牌真正的靈魂定位。
- 市場不缺品牌，缺的是被記住的品牌。
- 讓市場真正理解你的價值。
- 透過拆解 → 分析 → 重構，重新建立品牌競爭力。

【你能幫客戶做的事】
1. 回答品牌相關問題（定位、策略、行銷、命名等）
2. 介紹品牌靈魂建構所的服務內容與方案
3. 引導品牌建構問答（當客戶表達想做品牌診斷/分析時）
4. 提供行銷建議與品牌方向探索
5. AI 品牌工具建議
6. 個人 IP 定位分析
7. 日常對話與陪伴
8. 引導客戶預約品牌諮詢

【服務項目介紹】
① 品牌方向探索：品牌定位／品牌人格／市場方向分析
② 品牌升級與重構：品牌策略／商業模式／市場競爭力重建
③ AI 企業顧問：AI 品牌策略／AI 行銷整合／年約顧問
④ 創業陪跑系統：公司設立／個人品牌／商業模式規劃
⑤ 海外品牌拓展：國際市場定位／海外品牌策略
⑥ 企業內訓／包班課程：AI 品牌行銷／ChatGPT 商業應用

【單次顧問諮詢價目】
- 首次諮詢 30 分鐘：免費
- 顧問諮詢 1 小時：NT$ 6,000（適合初步諮詢、問題釐清、方向建議）
- 顧問諮詢 2 小時：NT$ 10,000（適合深入問題分析、策略方向建議）
- 半日顧問 4 小時：NT$ 25,000（適合全面性診斷、策略規劃建議）
- 全日顧問 8 小時：NT$ 45,000（適合完整問題梳理、深度策略擬定）
- 年度顧問方案（月約制）：另外洽詢，長期陪伴企業成長
- 企業優惠方案：另外洽詢，含企業客製化方案、團隊導入、內訓課程

【預約相關】
- 當客戶表達想預約、想諮詢、想了解更多時，提供預約連結
- 預約連結：{booking_url}
- 首次諮詢免費 30 分鐘，鼓勵客戶先預約體驗

【客戶常見問題的回答方向】
Q: 我現在品牌方向很亂，不知道問題出在哪？
A: 引導客戶先釐清現況，建議可以透過品牌診斷問答來找到方向，或預約免費 30 分鐘諮詢

Q: AI 到底能怎麼幫助我的品牌？
A: 說明 AI 可以協助品牌策略分析、內容生成、行銷自動化等，並介紹我們的 AI 企業顧問服務

Q: 我適合做個人品牌／創業嗎？
A: 引導客戶思考自身優勢與市場需求，建議可以透過品牌探索來找到答案

【禁忌與邊界】
- 絕對不隨意承諾保證收益
- 不攻擊競業品牌
- 不使用情緒化語言
- 不給不專業的法律／財務建議
- 不貶低客戶品牌
- 不強迫推銷
- 遇到無法回答的問題時，回覆：「這部分需要更完整了解您的品牌狀況，建議由品牌顧問進一步協助您分析 ✨」並引導預約品牌顧問或聯繫真人客服

【重要提醒】
- 你是一個能自然對話的 AI 顧問，不是只會跑問卷的機器人
- 客戶問什麼就回答什麼，像一個真正的品牌顧問在跟客戶聊天
- 只有當客戶明確表達想做品牌診斷/分析/問卷時，才引導進入品牌框架問答
- 回答要有深度但不要太長，控制在 200 字以內（除非客戶問了複雜問題）
- 用繁體中文回答
- 當客戶表達想預約或想進一步了解時，自然地提供預約連結
- 回覆中絕對不要使用 Markdown 格式（不用 *、**、#、## 等符號），直接用純文字回覆"""

# ===== 用戶狀態管理 =====
user_sessions = {}


def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "state": "chat",
            "step": 0,
            "answers": {},
            "role": None,
            "history": [],
            "service_code": None,
        }
    return user_sessions[user_id]


def reset_session(user_id):
    user_sessions[user_id] = {
        "state": "chat",
        "step": 0,
        "answers": {},
        "role": None,
        "history": [],
        "service_code": None,
    }


# ===== 問題框架定義 =====
QUESTIONS = {
    "enterprise": [
        {
            "key": "industry",
            "question": "請問貴公司主要經營的產業是什麼呢？\n（例如：科技、餐飲、美容、製造、服務業等）",
        },
        {
            "key": "scale",
            "question": "目前團隊的規模大約是？\n\n1. 1-10 人\n2. 11-50 人\n3. 50 人以上",
        },
        {
            "key": "revenue",
            "question": "方便透露目前的平均月營業額區間嗎？這能幫助我評估適合的策略方向 📈\n\n1. 50萬以下\n2. 50-200萬\n3. 200-500萬\n4. 500萬以上",
        },
        {
            "key": "target_age",
            "question": "您的產品或服務，主要鎖定哪個年齡層的客群？\n（可複選，直接輸入數字即可）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_client",
            "question": "如果用一句話描述您最理想的客戶，會是什麼樣的人？\n\n（例如：追求高質感的都會女性、注重效率的中小企業主等）",
        },
        {
            "key": "competitor",
            "question": "在市場上，您認為最主要的競爭對手或最常被比較的品牌是誰？\n\n（可以寫品牌名，或描述他們的類型）",
        },
        {
            "key": "pain_point",
            "question": "最後一個問題 💡\n\n目前經營上最大的痛點或挑戰是什麼？\n\n（例如：品牌辨識度不足、客戶不理解差異化、行銷投入與回報不成正比等）",
        },
    ],
    "personal": [
        {
            "key": "field",
            "question": "您目前經營的專業領域或主要分享的內容方向是什麼呢？\n（例如：美妝、健身、投資理財、心靈成長、設計等）",
        },
        {
            "key": "revenue",
            "question": "目前透過個人品牌帶來的平均月收入大約落在哪個區間？\n（這能幫助我規劃適合的變現策略）\n\n1. 3萬以下\n2. 3-10萬\n3. 10-30萬\n4. 30萬以上",
        },
        {
            "key": "target_age",
            "question": "您的受眾主要是哪個年齡層？\n（可複選，直接輸入數字即可）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_audience",
            "question": "您心目中最理想的受眾，是什麼樣的一群人？\n\n請用您自己的話描述看看。\n（例如：想提升專業形象的自由工作者、對品牌經營有興趣的創業新手等）",
        },
        {
            "key": "pain_point",
            "question": "目前經營個人品牌，最讓您感到卡關或想突破的痛點是什麼？\n\n（例如：定位不夠清晰、粉絲增長停滯、不知道如何變現等）",
        },
    ],
    "startup": [
        {
            "key": "industry",
            "question": "您目前正在哪個產業領域創業呢？\n（例如：SaaS、電商、教育科技、綠能、餐飲等）",
        },
        {
            "key": "scale",
            "question": "目前團隊有幾位成員？\n\n1. 1 人（獨立創業）\n2. 2-5 人\n3. 6-15 人\n4. 15 人以上",
        },
        {
            "key": "product_desc",
            "question": "請用最簡單的方式，描述一下您的產品或服務在解決什麼問題？\n\n（用一般人能理解的語言即可）",
        },
        {
            "key": "target_age",
            "question": "您主要想鎖定哪個年齡層的市場？\n（可複選，直接輸入數字即可）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_client",
            "question": "您想像中第一批會買單的客戶，大概是什麼樣的人？\n\n（例如：對新科技接受度高的年輕創業者、想數位轉型的傳統產業老闆等）",
        },
        {
            "key": "competitor",
            "question": "目前市場上有沒有類似的產品或服務？您認為最大的競爭對手是誰？\n\n（如果沒有直接競爭者，也可以說說替代方案是什麼）",
        },
        {
            "key": "pain_point",
            "question": "最後一個問題 💡\n\n目前創業過程中最大的挑戰或痛點是什麼？\n\n（例如：尚未找到 PMF、資金壓力、獲客成本過高等）",
        },
    ],
}

# ===== 歡迎訊息 =====
WELCOME_MESSAGE = """您好，我是心惠 ✨
品牌靈魂建構所的 AI 品牌顧問

很高興認識您。

無論您是想聊聊品牌方向、了解我們的服務，或是有任何品牌相關的問題，都歡迎直接跟我說。

如果您想做一次完整的品牌診斷分析，可以隨時告訴我「品牌診斷」。
想預約品牌顧問諮詢，可以告訴我「預約」✨"""

ROLE_MAP = {
    "1": "enterprise",
    "企業": "enterprise",
    "企業主": "enterprise",
    "2": "personal",
    "個人": "personal",
    "個人品牌": "personal",
    "3": "startup",
    "創業": "startup",
    "創業者": "startup",
}

ROLE_NAMES = {
    "enterprise": "企業主",
    "personal": "個人品牌經營者",
    "startup": "創業者",
}

# ===== 品牌診斷觸發關鍵字 =====
DIAGNOSIS_TRIGGERS = [
    "品牌診斷", "品牌分析", "品牌問卷", "開始診斷", "我想做品牌診斷",
    "品牌探索", "幫我分析", "品牌健檢",
    "start", "重新開始", "重來",
]

# ===== 六大服務數字選單引導流程 =====
# 客戶輸入 01~06（或 1~6）時，觸發對應服務的引導式對話
SERVICE_FLOWS = {
    "01": {
        "name": "品牌方向探索",
        "intro": """品牌方向探索？看來你現在有點迷惘喔 \U0001F60F
放心，迷路是找到對的路的第一步。

很多時候，我們覺得品牌做不起來，不是因為產品不好，而是「方向」一開始就偏了。

你目前覺得最大的卡點是什麼？
A. 不知道自己跟別人差在哪
B. 知道自己很好，但不知道怎麼說出來
C. 什麼都想做，結果什麼都做不好

（直接回覆 A、B 或 C，我幫你看看）""",
        "followup": """懂了。這其實是很多品牌的通病，你並不孤單啦 \U0001F609

真正的問題通常不在表面。我們的「品牌方向探索」會透過深度訪談和市場分析，幫你找出那個「只有你能做」的定位。

與其自己在那邊瞎猜，不如我們直接聊聊？

點這裡預約免費 30 分鐘諮詢，讓我聽聽你的故事：
👉 {booking_url}

期待跟你一起找到那個閃閃發光的定位 \u2728""",
    },
    "02": {
        "name": "品牌升級與重構",
        "intro": """喔？想做品牌升級與重構？
看來你已經不是新手了，是有點故事的品牌呢 \U0001F60E

品牌重構就像是老屋翻新，打掉重練很痛，但翻新後會很爽。

你現在最想「翻新」哪個部分？
A. 視覺跟不上現在的質感了
B. 商業模式想轉型，但品牌形象卡住了
C. 客群變了，以前的溝通方式不管用了

（回覆 A、B 或 C，讓我了解一下你的狀況）""",
        "followup": """看來是個大工程，但我最喜歡有挑戰性的案子了 \U0001F60F

品牌升級不是換個 Logo 就好，而是從策略、商業模式到市場競爭力的全面重建。

這部分文字說不清，我們需要好好坐下來拆解。

幫我留個時間，我們來一場深度的「品牌健檢」：
👉 {booking_url}

準備好迎接全新的自己了嗎？\u2728""",
    },
    "03": {
        "name": "AI 企業顧問",
        "intro": """終於有人問到我的強項了！
AI 企業顧問，這可是現在最聰明的選擇。

你知道嗎？現在不用 AI 的企業，就像在用算盤跟別人用電腦比速度。

你最想讓 AI 幫你解決什麼問題？
A. 行銷內容產出太慢，想自動化
B. 品牌策略沒靈感，需要 AI 當智囊
C. 團隊不懂 AI，想導入 AI 系統

（回覆 A、B 或 C，我看看怎麼幫你開外掛）""",
        "followup": """聰明！這正是 AI 能幫你大幅省下時間和成本的地方 \U0001F4A1

我們的「AI 企業顧問」不只教你用工具，而是幫你把 AI 整合進品牌策略和日常營運裡。

想知道 AI 怎麼為你的企業量身打造專屬方案嗎？

點這裡預約，我們來聊聊怎麼讓你的企業飛起來：
👉 {booking_url}

等你喔，未來的 AI 大師 \u2728""",
    },
    "04": {
        "name": "創業陪跑系統",
        "intro": """創業陪跑？看來你準備好要跳進這個坑了 \U0001F60F
創業這條路很孤單，但有我陪你，就不會那麼可怕啦。

你現在的進度到哪裡了？
A. 只有點子，還沒開始
B. 剛起步，但有點手忙腳亂
C. 已經在做，但需要有人幫忙梳理商業模式

（回覆 A、B 或 C，我看看你要從哪裡開始跑）""",
        "followup": """收到！不管你在哪個階段，我都準備好要當你的神隊友了 \U0001F609

我們的「創業陪跑系統」從公司設立、個人品牌到商業模式規劃，一路陪你打怪升級。

創業第一步：找個對的夥伴聊聊。

點這裡預約免費諮詢，讓我聽聽你的偉大計畫：
👉 {booking_url}

準備好一起衝了嗎？🚀""",
    },
    "05": {
        "name": "海外品牌拓展",
        "intro": """哇，眼光放得很遠喔！想出海了？\U0001F30D
出國比賽可不是開玩笑的，水很深呢。

你最想把品牌帶到哪裡去？
A. 歐美市場
B. 東南亞市場
C. 其他，我就是想走出台灣

（回覆 A、B 或 C，讓我看看你的野心有多大）""",
        "followup": """很有企圖心，我喜歡 \U0001F60F

每個市場的玩法都不一樣，直接把台灣的模式複製貼上通常會摔得很慘。

我們的「海外品牌拓展」會幫你重新定位國際市場，制定專屬的海外策略。

跨出海外的第一步，從跟我喝杯咖啡開始：
👉 {booking_url}

讓我們一起把品牌做到世界去吧！\u2728""",
    },
    "06": {
        "name": "企業內訓 / 包班課程",
        "intro": """企業內訓？看來你是個好老闆、好主管，想讓團隊一起升級 \U0001F44F

一個人強不夠，一群人強才是真的強。

你最想讓團隊學什麼？
A. AI 品牌行銷實戰
B. ChatGPT 商業應用
C. 品牌思維建立

（回覆 A、B 或 C，我幫你量身打造課程）""",
        "followup": """太棒了！這正是現在企業最需要的火力支援 \U0001F525

我們的課程不講空話，直接帶團隊實戰，保證上完課馬上能用。

每個企業的需求都不同，我們需要聊聊細節才能為你客製化。

點這裡預約討論，讓我們幫你的團隊開外掛：
👉 {booking_url}

期待在課堂上見到你們團隊喔！\u2728""",
    },
}

# 數字輸入正規化：把 1~6、01~06、全形數字都對應到 01~06
SERVICE_NUMBER_MAP = {
    "1": "01", "01": "01", "\uff10\uff11": "01", "\uff11": "01",
    "2": "02", "02": "02", "\uff10\uff12": "02", "\uff12": "02",
    "3": "03", "03": "03", "\uff10\uff13": "03", "\uff13": "03",
    "4": "04", "04": "04", "\uff10\uff14": "04", "\uff14": "04",
    "5": "05", "05": "05", "\uff10\uff15": "05", "\uff15": "05",
    "6": "06", "06": "06", "\uff10\uff16": "06", "\uff16": "06",
}

# 服務選單訊息（可在歡迎或客戶詢問服務時主動推送）
SERVICE_MENU_MESSAGE = """輸入下方數字，即可快速了解對應服務內容 \u2728
我會陪你一步步釐清方向，需要時也能安排專人為你深入分析。

01｜品牌方向探索
02｜品牌升級與重構
03｜AI 企業顧問
04｜創業陪跑系統
05｜海外品牌拓展
06｜企業內訓 / 包班課程

期待與你一起，打造真正能被市場記住的品牌。"""

# 服務選單觸發關鍵字
MENU_TRIGGERS = [
    "服務", "服務內容", "服務項目", "選單", "menu", "功能", "你們有什麼",
    "方案", "課程",
]

# ===== 預約觸發關鍵字 =====
BOOKING_TRIGGERS = [
    "預約", "我要預約", "預約諮詢", "想預約", "booking",
    "我想預約", "預約時間", "約時間", "想諮詢",
]

ROLE_SELECT_MESSAGE = """好的，讓我們開始品牌靈魂探索 ✨

首先，請告訴我您目前的身份：

1. 企業主（已有公司在經營）
2. 個人品牌（經營自媒體/個人IP）
3. 創業者（正在創業或準備創業）

請輸入 1、2 或 3"""


# ===== 取得預約 URL =====
def get_booking_url():
    """動態取得預約頁面 URL"""
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://line-brand-bot-xinhui.onrender.com")
    return f"{base_url}/booking"


# ===== AI 聊天函數 =====
def chat_with_ai(user_text, history):
    """使用 OpenAI 進行自然對話"""
    try:
        booking_url = get_booking_url()
        system_prompt = SYSTEM_PROMPT.replace("{booking_url}", booking_url)
        messages = [{"role": "system", "content": system_prompt}]

        # 加入最近的對話歷史（最多保留 10 輪）
        for h in history[-20:]:
            messages.append(h)

        messages.append({"role": "user", "content": user_text})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        # 移除 Markdown 格式符號
        reply = reply.replace('**', '').replace('*', '').replace('##', '').replace('###', '').replace('#', '')
        return reply
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        return "不好意思，我目前暫時無法回應。請稍後再試，或直接聯繫我們的品牌顧問為您服務 ✨"


# ===== AI 分析函數 =====
def build_analysis_prompt(role, answers):
    role_name = ROLE_NAMES.get(role, "用戶")
    answers_text = ""
    for key, value in answers.items():
        answers_text += f"- {key}: {value}\n"

    prompt = f"""以下是一位「{role_name}」完成品牌靈魂探索問卷後的回答：

{answers_text}

請根據以上資訊，為這位客戶產出一份專業的品牌分析報告：

## 1. 品牌定位分析
分析目前的市場定位，找出核心優勢與潛在機會點。

## 2. 品牌核心價值與故事建議
提煉品牌的核心價值主張，並撰寫一段 100-150 字的品牌故事草稿。

## 3. 品牌命名方向
提供 3 個符合品牌定位的命名建議，每個附上命名邏輯說明。

## 4. 行銷策略建議
針對客戶提到的痛點，給出 3 個具體且可執行的策略建議。

## 5. 品牌定位總結
用一句話總結這個品牌的核心定位（Positioning Statement）。

## 6. 下一步建議
建議客戶接下來可以採取的具體行動。

請用繁體中文回答，語氣專業有溫度，像一位資深品牌顧問在給客戶建議。"""

    return prompt


def generate_brand_analysis(role, answers):
    try:
        prompt = build_analysis_prompt(role, answers)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.replace("{booking_url}", get_booking_url())},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2500,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        # 移除 Markdown 格式符號
        reply = reply.replace('**', '').replace('*', '').replace('##', '').replace('###', '').replace('#', '')
        return reply
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "抱歉，分析過程中遇到了一些問題。請稍後再試，或輸入「品牌診斷」重新進行品牌診斷。"


# ===== 分段發送長訊息 =====
def split_message(text, max_length=4500):
    if len(text) <= max_length:
        return [text]
    messages = []
    current = ""
    lines = text.split("\n")
    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            messages.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        messages.append(current.strip())
    return messages


# ===== Email 通知 =====
def send_email_notification(booking_data):
    """發送預約通知 Email"""
    try:
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            logger.warning("SMTP not configured, skipping email notification")
            return False

        plan_names = {
            "free_30min": "首次諮詢 30 分鐘（免費）",
            "1hr": "顧問諮詢 1 小時（NT$ 6,000）",
            "2hr": "顧問諮詢 2 小時（NT$ 10,000）",
            "4hr": "半日顧問 4 小時（NT$ 25,000）",
            "8hr": "全日顧問 8 小時（NT$ 45,000）",
            "yearly": "年度顧問方案（另外洽詢）",
            "enterprise": "企業優惠方案（另外洽詢）",
        }

        plan_name = plan_names.get(booking_data.get("plan", ""), booking_data.get("plan", ""))

        subject = f"【新預約通知】{booking_data['name']} - {booking_data['date']} {booking_data['time']}"

        body = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✨ 新的品牌諮詢預約
━━━━━━━━━━━━━━━━━━━━━━━━

📋 客戶資料
姓名：{booking_data['name']}
電話：{booking_data['phone']}
Email：{booking_data['email']}
公司/品牌：{booking_data.get('company', '未填寫')}

📅 預約資訊
方案：{plan_name}
日期：{booking_data['date']}
時段：{booking_data['time']}

💡 諮詢方向
身份：{booking_data['identity']}
問題方向：{booking_data['topic']}

━━━━━━━━━━━━━━━━━━━━━━━━
預約時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = NOTIFY_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email notification sent to {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Email notification error: {e}")
        return False


# ===== LINE 通知管理者 =====
def send_line_notification(booking_data):
    """透過 LINE 推播通知管理者"""
    try:
        plan_names = {
            "free_30min": "首次諮詢 30 分鐘（免費）",
            "1hr": "顧問諮詢 1 小時（NT$ 6,000）",
            "2hr": "顧問諮詢 2 小時（NT$ 10,000）",
            "4hr": "半日顧問 4 小時（NT$ 25,000）",
            "8hr": "全日顧問 8 小時（NT$ 45,000）",
            "yearly": "年度顧問方案（另外洽詢）",
            "enterprise": "企業優惠方案（另外洽詢）",
        }

        plan_name = plan_names.get(booking_data.get("plan", ""), booking_data.get("plan", ""))

        notification = f"""✨ 新的品牌諮詢預約

📋 {booking_data['name']}
📞 {booking_data['phone']}
📧 {booking_data['email']}
🏢 {booking_data.get('company', '未填寫')}

📅 {booking_data['date']} {booking_data['time']}
📌 {plan_name}

💡 身份：{booking_data['identity']}
📝 方向：{booking_data['topic'][:100]}"""

        if ADMIN_LINE_USER_ID:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=ADMIN_LINE_USER_ID,
                        messages=[TextMessage(text=notification)],
                    )
                )
            logger.info(f"LINE notification sent to admin")
            return True
        else:
            logger.warning("ADMIN_LINE_USER_ID not set, skipping LINE notification")
            return False
    except Exception as e:
        logger.error(f"LINE notification error: {e}")
        return False


# ===== 預約頁面路由 =====
@app.route("/booking")
def booking_page():
    return render_template("booking.html")


@app.route("/api/booking", methods=["POST"])
def api_booking():
    """處理預約表單提交"""
    try:
        data = request.get_json()

        # 驗證必填欄位
        required_fields = ["name", "phone", "email", "plan", "date", "time", "identity", "topic"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"success": False, "message": f"請填寫{field}"}), 400

        # 儲存預約
        booking = {
            "id": len(bookings) + 1,
            "name": data["name"],
            "phone": data["phone"],
            "email": data["email"],
            "company": data.get("company", ""),
            "plan": data["plan"],
            "date": data["date"],
            "time": data["time"],
            "identity": data["identity"],
            "topic": data["topic"],
            "created_at": datetime.now().isoformat(),
        }
        bookings.append(booking)
        logger.info(f"New booking: {booking['name']} - {booking['date']} {booking['time']}")

        # 發送通知
        send_email_notification(booking)
        send_line_notification(booking)

        return jsonify({"success": True, "message": "預約成功"})
    except Exception as e:
        logger.error(f"Booking error: {e}")
        return jsonify({"success": False, "message": "系統錯誤，請稍後再試"}), 500


# ===== LINE Webhook 處理 =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.info(f"Received webhook: {body[:200]}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        # 即使出錯也回傳 200，避免 LINE 平台認為 bot 異常而將其踢出群組
    return "OK"


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    reset_session(user_id)
    save_known_user(user_id)  # 記錄新追蹤者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=WELCOME_MESSAGE)],
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        # 取得來源類型和 user_id
        source_type = event.source.type  # "user", "group", "room"
        user_id = getattr(event.source, 'user_id', None)
        user_text = event.message.text.strip()

        # 群組/聊天室中，使用 group_id 或 room_id 作為 push 目標
        if source_type == "group":
            push_target = event.source.group_id
        elif source_type == "room":
            push_target = event.source.room_id
        else:
            push_target = user_id

        # 如果無法取得 user_id（某些群組事件），使用 push_target 作為 session key
        session_key = user_id if user_id else push_target
        session = get_session(session_key)
        # 記錄用戶 user_id（僅記錄一對一用戶，不記錄群組）
        if source_type == "user" and user_id:
            save_known_user(user_id)
    except Exception as e:
        logger.error(f"Error in handle_message init: {e}")
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        state = session["state"]

        # ===== 聊天模式 =====
        if state == "chat":
            # 檢查是否輸入服務數字（01~06 / 1~6），觸發服務引導流程
            if user_text in SERVICE_NUMBER_MAP:
                service_code = SERVICE_NUMBER_MAP[user_text]
                flow = SERVICE_FLOWS[service_code]
                session["state"] = "service_flow"
                session["service_code"] = service_code
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=flow["intro"])],
                    )
                )
                return

            # 檢查是否要看服務選單
            if any(trigger in user_text for trigger in MENU_TRIGGERS):
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=SERVICE_MENU_MESSAGE)],
                    )
                )
                return

            # 檢查是否觸發預約
            if any(trigger in user_text for trigger in BOOKING_TRIGGERS):
                booking_url = get_booking_url()
                booking_msg = f"""當然可以 ✨

首次品牌諮詢 30 分鐘完全免費，讓我們先了解您的需求。

請點擊以下連結預約您方便的時間：
👉 {booking_url}

預約完成後，品牌顧問會在 24 小時內與您確認。

如果有任何問題，也歡迎繼續跟我聊 💡"""
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=booking_msg)],
                    )
                )
                return

            # 檢查是否觸發品牌診斷
            if any(trigger in user_text.lower() for trigger in DIAGNOSIS_TRIGGERS):
                session["state"] = "select_role"
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=ROLE_SELECT_MESSAGE)],
                    )
                )
                return

            # 自然聊天模式 - 使用 AI 回覆
            ai_response = chat_with_ai(user_text, session["history"])

            # 保存對話歷史
            session["history"].append({"role": "user", "content": user_text})
            session["history"].append({"role": "assistant", "content": ai_response})

            # 只保留最近 20 條歷史
            if len(session["history"]) > 20:
                session["history"] = session["history"][-20:]

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=ai_response)],
                )
            )
            return

        # ===== 服務引導流程模式（輸入 01~06 後，等待客戶回覆 A/B/C）=====
        elif state == "service_flow":
            service_code = session.get("service_code", "01")
            flow = SERVICE_FLOWS.get(service_code, SERVICE_FLOWS["01"])
            booking_url = get_booking_url()

            # 如果客戶又輸入其他服務數字，直接切換到那個服務的引導
            if user_text in SERVICE_NUMBER_MAP:
                new_code = SERVICE_NUMBER_MAP[user_text]
                session["service_code"] = new_code
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=SERVICE_FLOWS[new_code]["intro"])],
                    )
                )
                return

            # 不管客戶回什麼（A/B/C 或自由文字），都給出 followup 並導向預約
            followup_text = flow["followup"].replace("{booking_url}", booking_url)
            # 記錄這段對話進歷史，之後回到聊天時 AI 能陣脈延續
            session["history"].append({"role": "user", "content": f"（對 {flow['name']} 服務有興趣，回覆：{user_text}）"})
            session["history"].append({"role": "assistant", "content": followup_text})
            if len(session["history"]) > 20:
                session["history"] = session["history"][-20:]
            # 回到聊天模式，讓客戶能繼續自由提問，或輸入其他數字繼續探索
            session["state"] = "chat"
            session["service_code"] = None
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=followup_text)],
                )
            )
            return

        # ===== 選擇角色模式 =====
        elif state == "select_role":
            role = ROLE_MAP.get(user_text)
            if role:
                session["state"] = role
                session["role"] = role
                session["step"] = 0
                first_question = QUESTIONS[role][0]["question"]
                confirm_msg = f"了解，{ROLE_NAMES[role]}路線 ✨\n\n接下來我會問您 {len(QUESTIONS[role])} 個問題，完成後會為您產出一份品牌分析報告。\n\n"
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=confirm_msg + first_question)],
                    )
                )
            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="請輸入 1、2 或 3 來選擇您的身份：\n\n1. 企業主\n2. 個人品牌\n3. 創業者")],
                    )
                )
            return

        # ===== 問答模式 =====
        elif state in ["enterprise", "personal", "startup"]:
            # 允許用戶中途退出
            if user_text in ["取消", "退出", "結束"]:
                session["state"] = "chat"
                session["step"] = 0
                session["answers"] = {}
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="已退出品牌診斷。\n\n有任何問題隨時跟我說，或想重新開始可以輸入「品牌診斷」✨")],
                    )
                )
                return

            role = state
            step = session["step"]
            questions = QUESTIONS[role]

            current_key = questions[step]["key"]
            session["answers"][current_key] = user_text
            session["step"] += 1

            if session["step"] < len(questions):
                next_question = questions[session["step"]]["question"]
                progress = f"（{session['step'] + 1}/{len(questions)}）\n\n"
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=progress + next_question)],
                    )
                )
            else:
                session["state"] = "analyzing"
                thinking_msg = "收到，所有資訊已記錄完成 ✨\n\n正在為您進行品牌分析，請稍候約 30 秒..."

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=thinking_msg)],
                    )
                )

                try:
                    analysis = generate_brand_analysis(role, session["answers"])
                    messages_to_send = split_message(analysis)

                    for msg_text in messages_to_send:
                        line_bot_api.push_message(
                            PushMessageRequest(
                                to=push_target,
                                messages=[TextMessage(text=msg_text)],
                            )
                        )

                    booking_url = get_booking_url()
                    cta_msg = f"\n---\n\n以上是您的品牌靈魂初步分析報告 ✨\n\n如果您想要更深入的品牌策略規劃，歡迎預約品牌顧問進一步協助：\n👉 {booking_url}\n\n首次諮詢 30 分鐘免費，讓我們一起把品牌做到位 💡"

                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=push_target,
                            messages=[TextMessage(text=cta_msg)],
                        )
                    )
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=push_target,
                            messages=[TextMessage(text="抱歉，分析過程中遇到了一些問題。請稍後輸入「品牌診斷」重新嘗試。")],
                        )
                    )

                # 回到聊天模式
                session["state"] = "chat"
                session["step"] = 0
                session["answers"] = {}
            return

        # ===== 分析中模式 =====
        elif state == "analyzing":
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="正在分析中，請稍候片刻 ✨")],
                )
            )
            return


@handler.add(JoinEvent)
def handle_join(event):
    """心惠被加入群組或聊天室時自動打招呼"""
    try:
        logger.info(f"JoinEvent received: source_type={event.source.type}")
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            welcome = "大家好！我是心惠 ✨\n\nAI 品牌建構師，專門協助品牌定位、策略規劃與市場分析。\n\n有任何品牌相關的問題，歡迎直接問我 💡"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=welcome)],
                )
            )
    except Exception as e:
        logger.error(f"Error in handle_join: {e}")


# ===== 每日早安祝福功能 =====
DAILY_GREETING_SECRET = os.environ.get("DAILY_GREETING_SECRET", "xinhui-morning-2026")

# ===== 品牌知識分享主題庫（基於《創意世界建構師的實踐筆記》）=====
BRAND_KNOWLEDGE_TOPICS = [
    {
        "topic": "感知力：啟動你的創意雷達",
        "knowledge": """感知力是創意的第一步。它不只是「看到」，而是精準捕捉「有價值的信號」。
真正的感知力包含五個維度：視覺敏銳度（看到別人看不見的美學機會）、聽覺辨識力（用耳朵看世界）、
觸覺記憶力（在數位化世界中越來越稀缺珍貴）、嗅覺聯想力（氣味是最能喚起記憶和情感的感官）、
味覺分析力（學會分析一道菜的味道）。
最有價值的感知 = 洞察市場需求、預測消費趨勢、理解人性深層渴望。"""
    },
    {
        "topic": "價值感知的精準定位",
        "knowledge": """在品牌建構中，有四個關鍵問題能幫助你精準定位價值：
1. 這個創意，解決了什麼「真實的問題」？
2. 這個解決方案，比現有的方案，好在哪裡？
3. 目標受眾，願意為這個「更好」，支付多少溢價？
4. 這個「更好」，是否足夠明顯，能夠在嘈雜的市場中脫穎而出？
情感需求的洞察是關鍵——人類的行為很大程度上是由情感驅動的。
區分短暫的漣漪和改變海岸線的巨浪，才能預測真正的趨勢。"""
    },
    {
        "topic": "拆解力：從作品層面到系統層面",
        "knowledge": """拆解力就是逆向工程的能力。廚師拆解的是「食譜」，但企業家拆解的是「肯德基的中央廚房與全球供應鏈系統」。
真正的高手，不是拆解「作品」，而是拆解「系統」。
SOP 不是用來「限制」創意的，而是用來「解放」創意的。一套良好的 SOP 就像大腦的「外接硬碟」。
從「個人工匠」到「創意工業」的轉型，需要：專案啟動流程、檔案管理系統、品質檢查機制、客戶溝通協議、危機處理預案。"""
    },
    {
        "topic": "質變力：價值煉金術",
        "knowledge": """質變力是現代的「煉金術」，將平凡無奇的元素轉化為黃金。
三種最常用的煉金術：
1. 詩意美學：賦予獨特的美學風格
2. 故事敘事：包裹在動人的故事裡
3. 概念創新：重新定義品類，創造全新的「物種」
但質變不能只停留在「美學層面」，必須指向清晰的「商業目標」。
商業可行性才是關鍵的催化劑。"""
    },
    {
        "topic": "品牌價值視覺化的四個層次",
        "knowledge": """品牌視覺化有四個層次，從低到高：
1. 功能層：清晰展示產品的「是什麼」和「能做什麼」
2. 情感層：喚起目標受眾的特定情緒反應（尊貴感、獨特感、安全感）
3. 身份層：讓目標受眾感到「這反映了我是誰」，建立認同感
4. 文化層：將產品與更大的文化背景和社會價值觀連結起來
最高層次的品牌，不只是賣產品，而是在傳遞一種文化和價值觀。"""
    },
    {
        "topic": "重組力：建構品牌世界觀",
        "knowledge": """重組力是「拼圖的藝術」，將零散的創意元素有機地拼接在一起。
品牌需要統一世界觀，不能像違章建築。成功的「重組」需要堅實的「經濟地基」。
商業模式畫布的新思維：
- 顧客群體：不是「所有人」，而是精準的目標族群
- 價值主張：不是「產品思維」，而是「解決方案思維」
- 顧客關係：不是標準化服務，而是獨特的品牌體驗
量化不是要扼殺創意的靈魂，而是要給創意一個「骨架」。"""
    },
    {
        "topic": "輸出力：從創作者到資產建構者",
        "knowledge": """真正有遠見的創作者，不是將「時間」賣出好價錢，而是將「創意」轉化為持續產生「被動收入」的「資產」。
知識產品化的關鍵：將「一對一」轉為「一對多」。
七種創意資產類型：知識資產、工具資產、社群資產、品牌資產、智慧財產權、實體產品、數位產品。
關鍵思維轉變：要有「資產思維」而非「工作思維」。
每一次的創作，都不應該只是一次性的「交付」，而應該思考如何轉化為可持續產生價值的「資產」。"""
    },
    {
        "topic": "從才華到財富的橋樑",
        "knowledge": """創意的終點，不是一次性的大爆發，而是持續性的「價值創造」與「資產累積」。
成為「聰明的創造者」意味著：
- 不只創造感動自己的「作品」，要變成能解決問題、持續產生現金流的「產品」
- 不只成為技藝高超的「工匠」，要將技藝「系統化」、「流程化」，讓能力可以被複製
- 不只用時間換取「主動收入」，要建立「創意資產組合」獲取被動收入
從「才華」到「財富」的橋樑 = 商業模式。
一個健康的、可持續的商業模式，是守護創意純粹性的最堅固的「護城河」。"""
    }
]

@app.route("/daily-greeting", methods=["POST", "GET"])
def daily_greeting():
    """品牌知識分享 + 早安問候 - 由外部排程服務觸發（每兩天一次，共 15 天 = 8 則）"""
    # 驗證密鑰（避免被隨意觸發）
    secret = request.args.get("secret", "") or request.form.get("secret", "")
    if secret != DAILY_GREETING_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # 根據日期計算今天要用哪個主題（輪播 8 個主題）
        from datetime import date
        day_of_year = date.today().timetuple().tm_yday
        topic_index = (day_of_year // 2) % len(BRAND_KNOWLEDGE_TOPICS)
        today_topic = BRAND_KNOWLEDGE_TOPICS[topic_index]

        # 用 OpenAI 基於品牌知識生成有權威感的早安分享
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是心惠（潘心惠），一位專業的 AI 品牌建構師、創意世界建構師。
你正在為你的 LINE 好友撰寫一則「品牌知識早安分享」。

今天的主題是：「{today_topic['topic']}」

以下是你要分享的核心知識內容：
{today_topic['knowledge']}

請根據以上知識，撰寫一則訊息，格式如下：
1. 開頭用一句溫暖的早安問候（簡短即可，1-2 行）
2. 接著分享今天的品牌知識重點（用你自己的話重新詮釋，展現專業權威感）
3. 結尾加一個引導思考的問題或行動呼籲

要求：
- 語氣專業但有溫度，像一位值得信賴的品牌導師
- 展現權威感和深度洞察
- 控制在 200-280 字以內
- 適當使用 emoji 但不要過多（最多 3-4 個）
- 不要用「親愛的朋友」這種太通用的稱呼
- 可以用「✦」或「▸」等符號做重點標記"""
                },
                {
                    "role": "user",
                    "content": f"今天是 {datetime.now().strftime('%Y年%m月%d日 %A')}，請撰寫今天的品牌知識早安分享。"
                }
            ],
            max_tokens=500,
            temperature=0.8
        )
        greeting = response.choices[0].message.content.strip()

        # 優先使用 Broadcast 發送給「所有好友」；若失敗（如月度限額）再退回 Push 逐一發送
        messages = [TextMessage(text=greeting)]
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                line_bot_api.broadcast(BroadcastRequest(messages=messages))
                logger.info(f"Brand knowledge greeting BROADCAST to all friends (topic: {today_topic['topic']})")
                return jsonify({"success": True, "method": "broadcast", "topic": today_topic['topic'], "greeting": greeting}), 200
            except Exception as bc_err:
                # 月度限額（429）等情況：明確回報，並退回 Push 給已知用戶
                err_text = str(bc_err)
                logger.error(f"Broadcast failed: {err_text}; fallback to push")
                is_quota = "429" in err_text or "monthly limit" in err_text.lower() or "quota" in err_text.lower()

                known_users = load_known_users()
                if ADMIN_LINE_USER_ID and ADMIN_LINE_USER_ID not in known_users:
                    known_users.append(ADMIN_LINE_USER_ID)
                sent_count = 0
                failed_count = 0
                for uid in known_users:
                    try:
                        line_bot_api.push_message(
                            PushMessageRequest(to=uid, messages=messages)
                        )
                        sent_count += 1
                    except Exception as push_err:
                        logger.error(f"Push failed for {uid}: {push_err}")
                        failed_count += 1

                return jsonify({
                    "success": True if sent_count > 0 else False,
                    "method": "push_fallback",
                    "quota_exceeded": is_quota,
                    "topic": today_topic['topic'],
                    "greeting": greeting,
                    "sent": sent_count,
                    "failed": failed_count,
                    "total_users": len(known_users),
                    "broadcast_error": err_text
                }), (429 if is_quota else 200)

    except Exception as e:
        logger.error(f"Daily greeting error: {e}")
        return jsonify({"error": str(e)}), 500


# ===== IG 圖文導流功能 =====
# 儲存最近一次生成的 IG 內容（給管理員確認與圖片生成使用）
IG_CONTENT_FILE = "/tmp/ig_content_latest.json"

def _today_brand_topic():
    """根據日期取得今日品牌知識主題"""
    from datetime import date
    day_of_year = date.today().timetuple().tm_yday
    topic_index = (day_of_year // 2) % len(BRAND_KNOWLEDGE_TOPICS)
    return BRAND_KNOWLEDGE_TOPICS[topic_index]


@app.route("/ig-content", methods=["POST", "GET"])
def ig_content():
    """生成當日 IG 圖文內容：回傳「圖片標題重點」與「IG 貼文文案」
    供 Manus 排程任務用來生成藍金水紋風格圖片。
    """
    secret = request.args.get("secret", "") or request.form.get("secret", "")
    if secret != DAILY_GREETING_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        today_topic = _today_brand_topic()

        # 生成 IG 貼文文案（精煉、可直接複製貼上發布）
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是心惠（潘心惠），品牌靈魂建構所的 AI 品牌建構師。
你正在為 Instagram 撰寫一則品牌知識貼文文案。

今天的主題是：「{today_topic['topic']}」
核心知識內容：
{today_topic['knowledge']}

請輸出一則「可以直接複製貼上發布」的 IG 貼文文案，格式如下：
1. 第一行：一句吸睛的主標（帶 1 個 emoji）
2. 空一行
3. 一句引導提問或破題
4. 空一行
5. 用 ▸ 條列 3-4 個重點（精煉、每點一行）
6. 空一行
7. 一句品牌金句作結
8. 空一行
9. 一行 hashtag（6-8 個，含 #品牌靈魂建構所 #鏡水方舟）

要求：
- 文案精煉有重點，能吸引讀者，總字數約 150-220 字（不含 hashtag）
- 語氣專業有溫度，高端品牌顧問感
- 適度使用 emoji，不過度
- 用繁體中文"""
                },
                {
                    "role": "user",
                    "content": "請撰寫今天的 IG 品牌知識貼文文案。"
                }
            ],
            max_tokens=600,
            temperature=0.8
        )
        caption = response.choices[0].message.content.strip()

        # 整理圖片用的重點（直接取知識庫的條列，給圖片文字使用）
        result = {
            "topic": today_topic["topic"],
            "knowledge": today_topic["knowledge"],
            "caption": caption,
        }
        try:
            with open(IG_CONTENT_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving ig content: {e}")

        return jsonify({"success": True, **result}), 200

    except Exception as e:
        logger.error(f"ig_content error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/ig-broadcast", methods=["POST", "GET"])
def ig_broadcast():
    """收到 IG 貼文連結後，在 LINE 官方帳號發送導流訊息給所有追蹤者。
    參數：secret、ig_url（IG 貼文連結）、可選 title（主題）、image_url（預覽圖）
    發送方式：優先 Broadcast；若失敗則改用 Push 逐一發送已知用戶。
    """
    secret = request.args.get("secret", "") or request.form.get("secret", "")
    if secret != DAILY_GREETING_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    ig_url = request.args.get("ig_url", "") or request.form.get("ig_url", "")
    if not ig_url:
        return jsonify({"error": "missing ig_url"}), 400

    title = request.args.get("title", "") or request.form.get("title", "")
    image_url = request.args.get("image_url", "") or request.form.get("image_url", "")
    mode = request.args.get("mode", "broadcast") or request.form.get("mode", "broadcast")

    # 若沒帶 title，嘗試讀取最近生成的主題
    if not title:
        try:
            if os.path.exists(IG_CONTENT_FILE):
                with open(IG_CONTENT_FILE, "r", encoding="utf-8") as f:
                    title = json.load(f).get("topic", "")
        except Exception:
            pass

    topic_line = f"\u672c\u65e5\u4e3b\u984c\uff1a{title}\n\n" if title else ""
    promo_text = (
        f"\u54c1\u724c\u77e5\u8b58\u65b0\u8cbc\u6587\u4e0a\u7dda \u2728\n\n"
        f"{topic_line}"
        f"\u5b8c\u6574\u5167\u5bb9\u5df2\u767c\u4f48\u5728 Instagram\uff0c"
        f"\u9ede\u9032\u4f86\u770b\u770b\u4eca\u5929\u7684\u54c1\u724c\u601d\u8003 \ud83d\udc47\n"
        f"{ig_url}\n\n"
        f"\u5e02\u5834\u4e0d\u7f3a\u54c1\u724c\uff0c\u7f3a\u7684\u662f\u88ab\u8a18\u4f4f\u7684\u54c1\u724c\u3002"
    )

    messages = []
    if image_url:
        from linebot.v3.messaging import ImageMessage
        messages.append(ImageMessage(original_content_url=image_url, preview_image_url=image_url))
    messages.append(TextMessage(text=promo_text))

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            if mode == "broadcast":
                try:
                    line_bot_api.broadcast(BroadcastRequest(messages=messages))
                    logger.info(f"IG broadcast sent: {ig_url}")
                    return jsonify({"success": True, "method": "broadcast", "ig_url": ig_url}), 200
                except Exception as bc_err:
                    logger.error(f"Broadcast failed, fallback to push: {bc_err}")

            # Fallback：Push 逐一發送
            known_users = load_known_users()
            if ADMIN_LINE_USER_ID and ADMIN_LINE_USER_ID not in known_users:
                known_users.append(ADMIN_LINE_USER_ID)
            sent = 0
            failed = 0
            for uid in known_users:
                try:
                    line_bot_api.push_message(PushMessageRequest(to=uid, messages=messages))
                    sent += 1
                except Exception as pe:
                    logger.error(f"Push failed for {uid}: {pe}")
                    failed += 1
            return jsonify({"success": True, "method": "push", "sent": sent, "failed": failed, "ig_url": ig_url}), 200

    except Exception as e:
        logger.error(f"ig_broadcast error: {e}")
        return jsonify({"error": str(e)}), 500


# ===== IG Graph API 全自動發佈模組 =====
# 需要環境變數：IG_ACCESS_TOKEN、IG_BUSINESS_ACCOUNT_ID
import requests as _requests

IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_BUSINESS_ACCOUNT_ID = os.environ.get("IG_BUSINESS_ACCOUNT_ID", "")
IG_GRAPH_VERSION = os.environ.get("IG_GRAPH_VERSION", "v21.0")


def publish_to_instagram(image_url, caption):
    """透過 IG Graph API 發佈單張圖片貼文。
    回傳 (success: bool, result: dict)。成功時 result 含 permalink。
    """
    if not IG_ACCESS_TOKEN or not IG_BUSINESS_ACCOUNT_ID:
        return False, {"error": "IG_ACCESS_TOKEN 或 IG_BUSINESS_ACCOUNT_ID 未設定"}

    base = f"https://graph.facebook.com/{IG_GRAPH_VERSION}"
    try:
        # Step 1: 建立媒體容器
        create_resp = _requests.post(
            f"{base}/{IG_BUSINESS_ACCOUNT_ID}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": IG_ACCESS_TOKEN,
            },
            timeout=60,
        )
        create_data = create_resp.json()
        if "id" not in create_data:
            return False, {"error": "create_media_failed", "detail": create_data}
        creation_id = create_data["id"]

        # Step 2: 發佈容器
        publish_resp = _requests.post(
            f"{base}/{IG_BUSINESS_ACCOUNT_ID}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": IG_ACCESS_TOKEN,
            },
            timeout=60,
        )
        publish_data = publish_resp.json()
        if "id" not in publish_data:
            return False, {"error": "publish_failed", "detail": publish_data}
        media_id = publish_data["id"]

        # Step 3: 取得貼文連結 permalink
        permalink = ""
        try:
            perma_resp = _requests.get(
                f"{base}/{media_id}",
                params={"fields": "permalink", "access_token": IG_ACCESS_TOKEN},
                timeout=30,
            )
            permalink = perma_resp.json().get("permalink", "")
        except Exception as pe:
            logger.error(f"get permalink error: {pe}")

        return True, {"media_id": media_id, "permalink": permalink}

    except Exception as e:
        logger.error(f"publish_to_instagram error: {e}")
        return False, {"error": str(e)}


@app.route("/ig-publish", methods=["POST", "GET"])
def ig_publish():
    """全自動：接收 image_url + caption，發佈到 IG，成功後自動在 LINE 發送導流。
    參數：secret、image_url（公開圖片網址）、caption（IG 文案）、
          可選 title（主題）、line_notify（是否同步發 LINE 導流，預設 true）
    """
    secret = request.args.get("secret", "") or request.form.get("secret", "")
    if secret != DAILY_GREETING_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    image_url = request.args.get("image_url", "") or request.form.get("image_url", "")
    caption = request.args.get("caption", "") or request.form.get("caption", "")
    title = request.args.get("title", "") or request.form.get("title", "")
    line_notify = (request.args.get("line_notify", "true") or request.form.get("line_notify", "true")).lower() != "false"

    if not image_url:
        return jsonify({"error": "missing image_url"}), 400

    # 若沒帶 caption，嘗試讀取最近生成的內容
    if not caption:
        try:
            if os.path.exists(IG_CONTENT_FILE):
                with open(IG_CONTENT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    caption = data.get("caption", "")
                    if not title:
                        title = data.get("topic", "")
        except Exception:
            pass

    # Step 1: 發佈到 IG
    ok, ig_result = publish_to_instagram(image_url, caption)
    if not ok:
        return jsonify({"success": False, "stage": "ig_publish", "detail": ig_result}), 502

    permalink = ig_result.get("permalink", "")

    # Step 2: 在 LINE 發送導流
    line_result = None
    if line_notify and permalink:
        topic_line = f"\u672c\u65e5\u4e3b\u984c\uff1a{title}\n\n" if title else ""
        promo_text = (
            f"\u54c1\u724c\u77e5\u8b58\u65b0\u8cbc\u6587\u4e0a\u7dda \u2728\n\n"
            f"{topic_line}"
            f"\u5b8c\u6574\u5167\u5bb9\u5df2\u767c\u4f48\u5728 Instagram\uff0c"
            f"\u9ede\u9032\u4f86\u770b\u770b\u4eca\u5929\u7684\u54c1\u724c\u601d\u8003 \ud83d\udc47\n"
            f"{permalink}\n\n"
            f"\u5e02\u5834\u4e0d\u7f3a\u54c1\u724c\uff0c\u7f3a\u7684\u662f\u88ab\u8a18\u4f4f\u7684\u54c1\u724c\u3002"
        )
        from linebot.v3.messaging import ImageMessage
        messages = [
            ImageMessage(original_content_url=image_url, preview_image_url=image_url),
            TextMessage(text=promo_text),
        ]
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                try:
                    line_bot_api.broadcast(BroadcastRequest(messages=messages))
                    line_result = {"method": "broadcast"}
                except Exception as bc_err:
                    logger.error(f"Broadcast failed, fallback to push: {bc_err}")
                    known_users = load_known_users()
                    if ADMIN_LINE_USER_ID and ADMIN_LINE_USER_ID not in known_users:
                        known_users.append(ADMIN_LINE_USER_ID)
                    sent = 0
                    for uid in known_users:
                        try:
                            line_bot_api.push_message(PushMessageRequest(to=uid, messages=messages))
                            sent += 1
                        except Exception:
                            pass
                    line_result = {"method": "push", "sent": sent}
        except Exception as e:
            logger.error(f"line notify error: {e}")
            line_result = {"error": str(e)}

    return jsonify({
        "success": True,
        "ig": ig_result,
        "permalink": permalink,
        "line": line_result,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
