from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
) 
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    ImageMessage,
    TextMessage,
    Emoji,
    RichMenuSize,
    RichMenuRequest,
    RichMenuArea,
    RichMenuBounds,
    TemplateMessage,
    ConfirmTemplate,
    ImageCarouselTemplate,
    ImageCarouselColumn,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
    MessageAction,
    URIAction,
    DatetimePickerAction
)
from linebot.v3.webhooks import (
    FollowEvent,
    PostbackEvent,
    MessageEvent,
    TextMessageContent
)
import os
import psycopg2
import json
import requests
import urllib.parse


app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

def get_courses_list(day_name):
    supabase_url = os.getenv('DATABASE_URL')
    
    try:
        # 建立連線
        conn = psycopg2.connect(supabase_url)
        cur = conn.cursor()
        
        # 查詢課程，依照時間排序
        sql = """
            SELECT course_name, time_slot, location 
            FROM schedule 
            WHERE weekday = %s 
            ORDER BY time_slot
        """
        cur.execute(sql, (day_name,))
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return rows # 回傳原始資料列表 [(課名, 時間, 地點), (...)]
        
    except Exception as e:
        print(f"資料庫錯誤: {e}")
        return []


def get_thingspeak_chart_url():
    # 1. 設定 ThingSpeak 參數
    channel_id = os.getenv('THINKSPEAK_TEMP_CHANNEL_ID')
    read_api_key = os.getenv('THINKSPEAK_TEMP_READ_API_KEY')
    RESULTS_NUM = 8  # 想要顯示最近的幾筆資料
    
    # 取得 ThingSpeak 原始數據 (JSON)
    ts_url = f'https://api.thingspeak.com/channels/{channel_id}/fields/1.json?api_key={read_api_key}&results={RESULTS_NUM}&timezone=Asia/Taipei'
    response = requests.get(ts_url).json()
    
    # 解析數據
    feeds = response.get('feeds', [])
    labels = [f["created_at"][11:16] for f in feeds]  # 取得時間 (例如 14:30)
    data = [float(f["field1"]) if f["field1"] else 0 for f in feeds] # 取得數值
    
    # 2. 設定 QuickChart 配置 (Chart.js 語法)
    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "溫度(°C)",
                "data": data,
                "fill": True,
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "borderColor": "rgb(54, 162, 235)",
                "borderWidth": 2
            }]
        },
        "options": {
            "title": { "display": True, "text": "ThingSpeak溫度數據" }
        }
    }
    
    # 將字典轉換為字串並進行 URL 編碼
    json_str = json.dumps(chart_config)
    encoded_config = urllib.parse.quote(json_str)
    quickchart_url = f"https://quickchart.io/chart?c={encoded_config}&bkg=white"
    
    return quickchart_url


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@app.route("/create_rich_menu")
def create_rich_menu():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api_blob = MessagingApiBlob(api_client)

        # 建立 Rich Menu
        header = {
            'Authorization': 'Bearer ' + os.getenv('CHANNEL_ACCESS_TOKEN'),
            'Content-Type': 'application/json'
        }
        body = {
            "size": {
                "width": 2500,
                "height": 1686
            },
            "selected": True,
            "name": "圖文選單 1",
            "chatBarText": "查看更多資訊",
            "areas": [
                {
                    "bounds": {
                        "x": 21,
                        "y": 21,
                        "width": 794,
                        "height": 806
                    },
                    "action": {
                        "type": "message",
                        "text": "溫度"
                    }
                },
                {
                    "bounds": {
                        "x": 853,
                        "y": 18,
                        "width": 795,
                        "height": 810
                    },
                    "action": {
                        "type": "message",
                        "text": "濕度"
                    }
                },
                {
                    "bounds": {
                        "x": 17,
                        "y": 858,
                        "width": 794,
                        "height": 811
                    },
                    "action": {
                        "type": "message",
                        "text": "行事曆"
                    }
                },
                {
                    "bounds": {
                        "x": 848,
                        "y": 862,
                        "width": 799,
                        "height": 807
                    },
                    "action": {
                        "type": "message",
                        "text": "查詢課表"
                    }
                },
                {
                    "bounds": {
                        "x": 1681,
                        "y": 862,
                        "width": 801,
                        "height": 807
                    },
                    "action": {
                        "type": "message",
                        "text": "更多資訊"
                    }
                }
            ]
        }

        # ---------------------------------------------------
        #  Rich Menu 設定區塊 (已執行過，暫時封印)
        #  如果要更新選單圖片或配置，請再訪問該網頁一次
        #  https://line-bot-beta-two.vercel.app/create_rich_menu
        # ---------------------------------------------------
        # 發送請求建立圖文選單
        response = requests.post('https://api.line.me/v2/bot/richmenu', headers=header, data=json.dumps(body).encode('utf-8'))
        response = response.json()
        rich_menu_id = response['richMenuId']

        # 上傳圖文選單圖片
        image_url = 'https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/richmenu.jpg'
        img_response = requests.get(image_url)
        line_bot_api_blob.set_rich_menu_image(
            rich_menu_id=rich_menu_id,
            body=img_response.content,
            _headers={'Content-Type': 'image/jpeg'}
        )

        line_bot_api.set_default_rich_menu(rich_menu_id)

    return 'Rich menu created'

# 加入好友事件
@line_handler.add(FollowEvent)
def handle_follow(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        confirm_template = ConfirmTemplate(
            text="你今天學程式了嗎",
            actions=[
                PostbackAction(label="是", data="study_yes"),
                PostbackAction(label="否", data="study_no"),
            ]
        )
        template_message = TemplateMessage(
            alt_text='Confirm alt text',
            template=confirm_template
        )

        emojis_list = [
            Emoji(index=0, product_id="5ac22e85040ab15980c9b44f", emoji_id="008"),
            Emoji(index=16, product_id="670e0cce840a8236ddd4ee4c", emoji_id="019"),
            Emoji(index=18, product_id="5ac22e85040ab15980c9b44f", emoji_id="008")  
        ]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages = [TextMessage(text="$ 你好!歡迎加入聯大資訊工程系$ $", emojis=emojis_list),
                            template_message]
            )
        )


# postback事件
@line_handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if data == "study_yes":
            line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="很棒!請繼續保持")]
            )
        )
        elif data == "study_no":
            line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="加油!每天進步一點點")]
            )
        )

# 訊息事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 定義有效的星期列表 (用來檢查使用者輸入是否合法)
        valid_days = [
            "星期一", "星期二", "星期三", "星期四", 
            "星期五", "星期六", "星期日"
        ]

        # 1. 查詢課表：跳出 Quick Reply
        if text == "查詢課表":
            items = [
                QuickReplyItem(action=MessageAction(label="星期一", text="星期一")),
                QuickReplyItem(action=MessageAction(label="星期二", text="星期二")),
                QuickReplyItem(action=MessageAction(label="星期三", text="星期三")),
                QuickReplyItem(action=MessageAction(label="星期四", text="星期四")),
                QuickReplyItem(action=MessageAction(label="星期五", text="星期五")),
            ]
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="請選擇想查詢的日期:",
                            quick_reply=QuickReply(items=items)
                        )
                    ]
                )
            )

        # 直接判斷：如果使用者輸入的是「星期幾」
        elif text in valid_days:
            # 不需要轉換了，直接拿 text (例如 "星期一") 去資料庫查
            course_rows = get_courses_list(text)
                
            reply_messages_list = []

            if not course_rows:
                reply_messages_list.append(TextMessage(text=f"{text}沒有課,可以好好休息!也別忘了要練習程式喔"))
            else:
                # 1. 先放一個標題
                reply_messages_list.append(TextMessage(text=f"{text}的課表如下"))
                # 2. 把查到的課程加入列表
                for row in course_rows:
                    course_name = row[0]
                    time_slot = row[1]
                    location = row[2]
                        
                    msg_text = f"課程名稱: {course_name}\n時間: {time_slot}\n教室: {location}"
                    reply_messages_list.append(TextMessage(text=msg_text))

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=reply_messages_list
                )
            )  

        # 2. 行事曆
        elif text == "行事曆":
            supabase_image_url_1 = "https://jfnhxrcdlhajyhuadxkx.supabase.co/storage/v1/object/public/picture/114-1Calendar.png"
            supabase_image_url_2 = "https://jfnhxrcdlhajyhuadxkx.supabase.co/storage/v1/object/public/picture/114-2Calendar.png"

            image_message_1 = ImageMessage(
                original_content_url = supabase_image_url_1,            # 原始大小
                preview_image_url = supabase_image_url_1
            )
            image_message_2 = ImageMessage(
                original_content_url = supabase_image_url_2,            # 原始大小
                preview_image_url = supabase_image_url_2
            )

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="114學年行事曆(上下學期)")
                            , image_message_1, image_message_2]
                )
            ) 

        # 3. 更多資訊
        elif text == "更多資訊":
            image_carousel_template = ImageCarouselTemplate(
                columns=[
                    ImageCarouselColumn(
                        image_url='https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/school_web.jpg',
                        action = URIAction(
                            label="訪問聯大總網",
                            uri="https://www.nuu.edu.tw/"
                        )
                    ),
                    ImageCarouselColumn(
                        image_url='https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/imf.png',
                        action = URIAction(
                            label="訪問校務資訊系統",
                            uri="https://eap10.nuu.edu.tw/Login.aspx?logintype=S"
                        )
                    ),
                    ImageCarouselColumn(
                        image_url='https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/csie.png',
                        action = URIAction(
                            label="訪問資工系網頁",
                            uri="https://csie.nuu.edu.tw/"
                        )
                    ),
                    ImageCarouselColumn(
                        image_url='https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/fb.png',
                        action = URIAction(
                            label="訪問系學會fb",
                            uri="https://www.facebook.com/CSIEofNUU/"
                        )
                    ),
                    ImageCarouselColumn(
                        image_url='https://raw.githubusercontent.com/Ya-Fong/line-bot/main/public/ig.jpg',
                        action = URIAction(
                            label="訪問系學會ig",
                            uri="https://www.instagram.com/nuu_csie_/"
                        )
                    )
                ]
            )
            image_carousel_message = TemplateMessage(
                alt_text='圖片傳播範本',
                template=image_carousel_template
            )

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[image_carousel_message]
                )
            )

        # 4. 溫度
        elif text == "溫度":
            QuickChart_image_url = get_thingspeak_chart_url()
            
            image_message = ImageMessage(
                original_content_url = QuickChart_image_url,            # 原始大小
                preview_image_url = QuickChart_image_url
            )
            # Line Bot 回傳圖片訊息
            # 注意：original_content_url 與 preview_image_url 都必須是 HTTPS
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="即時溫度變化圖")
                            , image_message]
                )
            )

        # 5. 濕度

        # 6. 其他訊息
        else:
            if text != "是" and text != "否":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="我不清楚你在說什麼，可以看看下方資訊欄位喔")]   
                    )
                )
            
