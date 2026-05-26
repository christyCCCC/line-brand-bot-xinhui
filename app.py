"""
LINE AI 品牌建構師「心惠」- 主程式
鏡水方舟品牌靈魂提煉系統
"""

import os
import json
import logging
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, FollowEvent
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

# LINE SDK 設定
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ===== 用戶狀態管理 =====
user_sessions = {}


def get_session(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "state": "idle",
            "step": 0,
            "answers": {},
            "role": None,
        }
    return user_sessions[user_id]


def reset_session(user_id):
    user_sessions[user_id] = {
        "state": "idle",
        "step": 0,
        "answers": {},
        "role": None,
    }


# ===== 問題框架定義 =====
QUESTIONS = {
    "enterprise": [
        {
            "key": "industry",
            "question": "原來是大老闆！失敬失敬\n\n請問貴公司主要是做什麼產業的呢？\n（例如：科技、餐飲、美容、製造...）",
        },
        {
            "key": "scale",
            "question": "了解了解！那目前團隊的規模大概是？\n\n1. 1-10 人\n2. 11-50 人\n3. 50 人以上",
        },
        {
            "key": "revenue",
            "question": "這個問題比較現實一點\n\n方便透露目前的平均月營業額區間嗎？這能幫我評估適合的策略量級喔！\n\n1. 50萬以下\n2. 50-200萬\n3. 200-500萬\n4. 500萬以上",
        },
        {
            "key": "target_age",
            "question": "你們的產品/服務，最想賣給哪個年齡層的人？\n（可以複選，直接打數字就好！）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_client",
            "question": "如果用一句話形容你最完美的客人，你會怎麼說？\n\n（例如：喜歡追求高質感的都會女性、注重效率的中小企業主...隨便你怎麼形容！）",
        },
        {
            "key": "competitor",
            "question": "在市場上，你覺得誰是你們最大的假想敵？或是最常被拿來比較的對象？\n\n（可以寫品牌名、公司名，或描述一下他們是什麼類型的競爭者）",
        },
        {
            "key": "pain_point",
            "question": "最後一個問題！\n\n現在經營上讓你最頭痛、最想翻白眼的問題是什麼？\n\n（例如：品牌知名度不夠、客戶不知道我們的差異化、行銷預算花了沒效果...）",
        },
    ],
    "personal": [
        {
            "key": "field",
            "question": "個人品牌超棒的！展現獨特魅力的時代來了\n\n你的專業領域或主要分享的內容是什麼呢？\n（例如：美妝、健身、投資理財、心靈成長...）",
        },
        {
            "key": "revenue",
            "question": "目前靠個人品牌帶來的平均月收入大概落在哪個區間呢？\n（這能幫我規劃變現策略喔）\n\n1. 3萬以下\n2. 3-10萬\n3. 10-30萬\n4. 30萬以上",
        },
        {
            "key": "target_age",
            "question": "你的粉絲或受眾，主要是哪個年齡層？\n（可以複選，直接打數字！）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_audience",
            "question": "你心目中最鐵的粉絲，大概是什麼樣的一群人？\n\n用你自己的話形容看看！\n（例如：想要變美但不知道從哪開始的小資女、對被動收入有興趣的上班族...）",
        },
        {
            "key": "pain_point",
            "question": "經營個人品牌很累吧！\n\n現在讓你覺得最卡關、最想突破的痛點是什麼？\n\n（例如：粉絲增長停滯、不知道怎麼變現、內容產出壓力大...）",
        },
    ],
    "startup": [
        {
            "key": "industry",
            "question": "充滿熱血的創業者！我喜歡你的衝勁\n\n你們正在哪個產業闖蕩呢？\n（例如：SaaS、電商、教育科技、綠能...）",
        },
        {
            "key": "scale",
            "question": "目前的團隊有幾位神隊友了？\n\n1. 只有我 1 人（超級英雄模式）\n2. 2-5 人\n3. 6-15 人\n4. 15 人以上",
        },
        {
            "key": "product_desc",
            "question": "用最簡單白話的方式，跟我介紹一下你們的產品或服務在解決什麼問題吧！\n\n（想像你在跟阿嬤解釋你在做什麼）",
        },
        {
            "key": "target_age",
            "question": "你們想主攻哪個年齡層的市場？\n（可以複選，直接打數字！）\n\n1. 18-24 歲\n2. 25-34 歲\n3. 35-44 歲\n4. 45 歲以上",
        },
        {
            "key": "ideal_client",
            "question": "你想像中第一個會掏錢買單的客人，長什麼樣子？有什麼特徵？\n\n（例如：對新科技接受度高的年輕創業者、想數位轉型的傳統產業老闆...）",
        },
        {
            "key": "competitor",
            "question": "目前市場上有沒有類似的產品？你覺得誰是最大的競爭對手？\n\n（如果覺得沒有直接競爭者，也可以說說替代方案是什麼）",
        },
        {
            "key": "pain_point",
            "question": "創業維艱，現在最讓你睡不著覺的最大痛點是什麼？\n\n（例如：找不到 PMF、資金燒太快、不知道怎麼獲客...）",
        },
    ],
}

# ===== 歡迎訊息 =====
WELCOME_MESSAGE = """哈囉！我是心惠
鏡水方舟的 AI 品牌建構師

要打造一個讓人著迷的品牌，我們得先確認你的「原廠設定」。

告訴我，你目前是哪一種身份呢？

1. 企業主
2. 個人品牌
3. 創業者

（直接輸入數字 1、2 或 3 就可以囉！）"""

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
    "personal": "個人品牌",
    "startup": "創業者",
}


# ===== AI 分析函數 =====
def build_analysis_prompt(role, answers):
    role_name = ROLE_NAMES.get(role, "用戶")
    answers_text = ""
    for key, value in answers.items():
        answers_text += f"- {key}: {value}\n"

    prompt = f"""你是「心惠」，鏡水方舟的 AI 品牌建構師。你的個性是水瓶座風格——活潑有趣、有點古靈精怪，偶爾會冒出有創意的比喻或幽默，但同時具備深厚的品牌策略知識。

以下是一位「{role_name}」完成品牌靈魂提煉問卷後的回答：

{answers_text}

請根據以上資訊，用心惠的口吻，為這位用戶產出以下品牌分析報告：

## 1. 品牌人格 (Brand Persona)
用一個生動的比喻或角色來描述這個品牌的靈魂。像是在描述一個有血有肉的人物一樣。

## 2. 品牌故事 (Brand Story)
寫一段 100-150 字的品牌核心論述草稿，要能打動目標客群的心。

## 3. 品牌命名方向 (Naming Ideas)
提供 3 個符合品牌定位的命名建議，每個附上簡短的命名邏輯說明。

## 4. 行銷策略建議 (Marketing Strategy)
針對用戶提到的痛點，給出 3 個具體且可執行的突破性建議。

## 5. 品牌定位總結 (Brand Positioning)
用一句話總結這個品牌的核心定位（Positioning Statement）。

請用繁體中文回答，語氣保持心惠的風格——專業但不死板，有趣但不輕浮。適度使用 emoji 增加親和力。"""

    return prompt


def generate_brand_analysis(role, answers):
    try:
        prompt = build_analysis_prompt(role, answers)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是心惠，鏡水方舟的 AI 品牌建構師。水瓶座，活潑有趣但專業。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.8,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "哎呀！我的腦袋暫時當機了，請稍後再試一次，或輸入「開始」重新來過！"


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
    user_id = event.source.user_id
    user_text = event.message.text.strip()
    session = get_session(user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 特殊指令處理
        if user_text.lower() in ["開始", "重新開始", "start", "重來", "hi", "你好", "哈囉"]:
            reset_session(user_id)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=WELCOME_MESSAGE)],
                )
            )
            return

        state = session["state"]

        if state == "idle":
            role = ROLE_MAP.get(user_text)
            if role:
                session["state"] = role
                session["role"] = role
                session["step"] = 0
                first_question = QUESTIONS[role][0]["question"]
                confirm_msg = f"好的！{ROLE_NAMES[role]}路線啟動\n\n那我們開始囉！一共 {len(QUESTIONS[role])} 個問題，回答完我就幫你提煉品牌靈魂！\n\n"
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
                        messages=[TextMessage(text=WELCOME_MESSAGE)],
                    )
                )
            return

        elif state in ["enterprise", "personal", "startup"]:
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
                thinking_msg = "收到！你的大腦電波我已經全部接收完畢\n\n給我大概 30 秒，我來幫你提煉品牌靈魂...\n\n腦力激盪中..."

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
                                to=user_id,
                                messages=[TextMessage(text=msg_text)],
                            )
                        )

                    cta_msg = "\n\n---\n\n以上就是你的品牌靈魂初步分析！\n\n想要更完整的品牌策略規劃？\n鏡水方舟的專業顧問團隊可以幫你把這些洞察變成實際的品牌行動方案\n\n輸入「開始」可以重新測驗"

                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text=cta_msg)],
                        )
                    )
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=user_id,
                            messages=[TextMessage(text="哎呀！分析過程中遇到了一點小問題\n\n請輸入「開始」重新來過！")],
                        )
                    )

                reset_session(user_id)
            return

        elif state == "analyzing":
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="我還在努力分析中喔！請再等我一下下")],
                )
            )
            return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
