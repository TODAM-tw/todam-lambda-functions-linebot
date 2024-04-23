# -*- coding: utf-8 -*-

import json
import os
import time
from datetime import datetime

import boto3
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (ApiClient, AudioMessage, Configuration,
                                  ImageMessage, MessagingApi, MessagingApiBlob,
                                  ReplyMessageRequest,
                                  ShowLoadingAnimationRequest, TextMessage,
                                  VideoMessage)
from linebot.v3.webhooks import (AudioMessageContent, FileMessageContent,
                                 ImageMessageContent, MessageEvent,
                                 StickerMessageContent, TextMessageContent,
                                 VideoMessageContent)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(channel_secret=CHANNEL_SECRET)

aws_access_key_id = os.environ["AWS_CLIENT_ACCESS_KEY_ID"]
aws_secret_access_key = os.environ["AWS_CLIENT_SECRET_ACCESS_KEY"]
aws_bucket_arn = os.environ["AWS_CLIENT_BUCKET_ARN"]
aws_region_name = os.environ["AWS_CLIENT_REGION_NAME"]
aws_bucket_name = os.environ["AWS_CLIENT_BUCKET_NAME"]

s3_client = boto3.client(
    "s3",
    aws_access_key_id = aws_access_key_id,
    aws_secret_access_key = aws_secret_access_key,
    region_name=aws_region_name
)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    reply_messages = []

    with ApiClient(configuration) as api_client:
        start_time = time.time()
        line_bot_api = MessagingApi(api_client)
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chat_id=event.source.user_id,
            )
        )

        # Test Model API Here
        if event.message.text == "OUR_SCENARIO_HERE":
            reply_messages = mock_model_api_prototype()

        # Add some reserve word to trigger the specific response
        elif event.message.text == "我想知道 AWS 的16項領導力準則":
            reply_messages = [
                'AWS ☁️ 的創辦故事始於 2003 年，當時亞馬遜公司的 Jeff Bezos 意識到他們在建設強大的內部基礎設施方面取得了不錯的進展！',
                '他認識到這個基礎設施可以成為一個強大的雲端運算平台，能夠為其他企業提供服務。於是在 2006 年，AWS ☁️ 正式推出，開始提供雲端服務。',
                'AWS ☁️ 的成功與其開放性、靈活性和不斷創新的企業文化有關。',
                '這一切都源於 Jeff Bezos 對技術和未來的敏銳洞察力✨，他能看到潛在的機會並推動公司朝著新的方向發展。',
            ]
        elif event.message.text == "我想知道 AWS 創辦故事":
            reply_messages = [
                f'AWS ☁️ 的創辦故事始於 2003 年，當時亞馬遜公司的 Jeff Bezos 意識到他們在建設強大的內部基礎設施方面取得了不錯的進展！',
                f'他認識到這個基礎設施可以成為一個強大的雲端運算平台，能夠為其他企業提供服務。於是在 2006 年，AWS ☁️ 正式推出，開始提供雲端服務。',
                f'AWS ☁️ 的成功與其開放性、靈活性和不斷創新的企業文化有關。',
                f'這一切都源於 Jeff Bezos 對技術和未來的敏銳洞察力✨，他能看到潛在的機會並推動公司朝著新的方向發展。',
            ]
        
        # 
        else:
            reply_messages = [
                "DAMMMM 蟹 Bro, M3 換一句試試吧！",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                f"Time elapsed: {time.time() - start_time} seconds."
            ]

        reply_messages = [TextMessage(text=message) for message in reply_messages]

        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=reply_messages,
            )
        )

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event: MessageEvent):
    if event.source.type != "user":
        return
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chat_id=event.source.user_id,
            )
        )

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="$", emojis=[{"index": 0, "productId": "5ac21c46040ab15980c9b442", "emojiId": "138"}])]
            )
        )

@handler.add(MessageEvent, message=(ImageMessageContent,
                                    VideoMessageContent,
                                    AudioMessageContent))
def handle_content_message(event: MessageEvent):
    """
    The timeout for Lambda Functions here is only 3 seconds, 
    which is insufficient for uploading files to S3. 
    Please increase the timeout to 10 seconds or possibly more.
    """
    start_time = time.time()
    if isinstance(event.message, ImageMessageContent):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessageContent):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessageContent):
        ext = 'm4a'
    else:
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.show_loading_animation(
            ShowLoadingAnimationRequest(
                chat_id=event.source.user_id,
            )
        )

        line_bot_blob_api = MessagingApiBlob(api_client)

        store_img_to_s3(event, ext, line_bot_blob_api)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="Save content."),
                    TextMessage(text=f"Time elapsed: {time.time() - start_time} seconds.")
                ]
            )
        )

@staticmethod
def lambda_handler(event, context):
    try: 
        body = event["body"]
        signature = event["headers"]["x-line-signature"]

        # Here we don"t need to parse the body because it"s already a string
        # body = json.loads(body)
        store_user_log(body)

        handler.handle(body, signature)

        return {
            "statusCode": 201,
            "body": json.dumps("Hello from Lambda!")
        }
    except InvalidSignatureError:
        return {
            "statusCode": 400,
            body: "Invalid signature"
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(str(e))
        }

@staticmethod
def get_source_id(event: MessageEvent) -> str:
    if event.source.type == 'user':
        source_id = event.source.user_id
    elif event.source.type == 'group':
        source_id = event.source.group_id
    elif event.source.type == 'room':
        source_id = event.source.room_id
    return source_id

@staticmethod
def store_img_to_s3(
        event: MessageEvent, ext: str, 
        line_bot_blob_api: MessagingApiBlob) -> None:
    source_id = get_source_id(event)
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

    # Save the content to /tmp folder or lambda will not have permission to access it
    user_uploaded_image_file_name = f"/tmp/{source_id}-{current_time}.{ext}"
    s3_goal_file_path = f"{ext}/{source_id}-{current_time}.{ext}"

    message_content = line_bot_blob_api.get_message_content(message_id=event.message.id)
    with open(user_uploaded_image_file_name, 'wb') as tf:
        tf.write(message_content)

    s3_client.upload_file(user_uploaded_image_file_name, aws_bucket_name, s3_goal_file_path)
    os.remove(user_uploaded_image_file_name)

@staticmethod
def store_user_log(body: str) -> None:
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

    s3_goal_file_path = f"logs/{current_time}.log"
    lambda_tmp_file_file = "/tmp/events.log"

    with open(lambda_tmp_file_file, "a", encoding="utf-8") as f:
        f.write(f"{body}\n")
    s3_client.upload_file(lambda_tmp_file_file, aws_bucket_name, s3_goal_file_path)
    os.remove(lambda_tmp_file_file)


@staticmethod
def mock_model_api_prototype() -> list[str]:
    """
    This is the prototype of calling the model API.
    Change this function to your model API.
    """
    return ["Hi", "HiHi", "HiHi"]
