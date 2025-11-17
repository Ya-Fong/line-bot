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
    ReplyMessageRequest,
    TextMessage,
    Emoji,
    TemplateMessage,
    ConfirmTemplate,
    ImageCarouselTemplate,
    ImageCarouselColumn,
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


app = Flask(__name__)

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
line_handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


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

        url = "https://line-bot-eta-one.vercel.app"
        image_carousel_template = ImageCarouselTemplate(
            columns=[
                ImageCarouselColumn(
                    image_url=url+'/school_web.jpg',
                    action = URIAction(
                        label="訪問聯大總網",
                        uri="https://www.nuu.edu.tw/"
                    )
                ),
                ImageCarouselColumn(
                    image_url=url+'/imf.png',
                    action = URIAction(
                        label="訪問校務資訊系統",
                        uri="https://eap10.nuu.edu.tw/Login.aspx?logintype=S"
                    )
                ),
                ImageCarouselColumn(
                    image_url=url+'/csie.png',
                    action = URIAction(
                        label="訪問資工系網頁",
                        uri="https://csie.nuu.edu.tw/"
                    )
                ),
                ImageCarouselColumn(
                    image_url=url+'/fb.png',
                    action = URIAction(
                        label="訪問系學會fb",
                        uri="https://www.facebook.com/CSIEofNUU/"
                    )
                ),
                ImageCarouselColumn(
                    image_url=url+'/ig.jpg',
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

        emojis_list = [
            Emoji(index=0, product_id="5ac22e85040ab15980c9b44f", emoji_id="008"),
            Emoji(index=16, product_id="670e0cce840a8236ddd4ee4c", emoji_id="019"),
            Emoji(index=18, product_id="5ac22e85040ab15980c9b44f", emoji_id="008")  
        ]
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages = [TextMessage(text="$ 你好!歡迎加入聯大資訊工程系$ $", emojis=emojis_list),
                            template_message,
                            image_carousel_message]
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

        if text != "是" and text != "否":
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="我不清楚你在說什麼，可以看看上方資訊欄位喔")]   
                )
            )
            

