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
        }
    return user_sessions[user_id]


def reset_session(user_id):
    user_sessions[user_id] = {
        "state": "chat",
        "step": 0,
        "answers": {},
        "role": None,
        "history": [],
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
    except Exception as e:
        logger.error(f"Error in handle_message init: {e}")
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        state = session["state"]

        # ===== 聊天模式 =====
        if state == "chat":
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
