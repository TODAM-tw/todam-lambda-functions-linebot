# -*- coding: utf-8 -*-

import json
import os
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

aws_region_name = os.environ["AWS_CLIENT_REGION_NAME"]
aws_bucket_name = os.environ["AWS_CLIENT_BUCKET_NAME"]

s3_client = boto3.client(
    "s3",
    region_name=aws_region_name
)

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    """
    Only handle the text message event, but do nothing.

    In the future, we may add the model to check the message
    explicitly or not, and then suggest the user to resend the message.
    """
    ...
    return

@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker_message(event: MessageEvent):
    if event.source.type != "user":
        return
    return

@handler.add(MessageEvent, message=(ImageMessageContent,
                                    VideoMessageContent,
                                    AudioMessageContent))
def handle_content_message(event: MessageEvent):
    """
    The timeout for Lambda Functions here is only 3 seconds, 
    which is insufficient for uploading files to S3. 
    Please increase the timeout to 10 seconds or possibly more.
    """
    if isinstance(event.message, ImageMessageContent):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessageContent):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessageContent):
        ext = 'm4a'
    else:
        return

    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)

        store_img_to_s3(event, ext, line_bot_blob_api)

    return

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

    mimetype = 'image/jpeg'

    s3_client.upload_file(
        Filename=user_uploaded_image_file_name, 
        Bucket=aws_bucket_name, 
        Key=s3_goal_file_path, 
        ExtraArgs={
            "ContentType": mimetype
        }
    )
    os.remove(user_uploaded_image_file_name)

@staticmethod
def store_user_log(body: str) -> None:
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

    s3_goal_file_path = f"{current_time}.log"
    lambda_tmp_file_file = "/tmp/events.log"

    with open(lambda_tmp_file_file, "a", encoding="utf-8") as f:
        f.write(f"{body}\n")
    s3_client.upload_file(lambda_tmp_file_file, aws_bucket_name, s3_goal_file_path)
    os.remove(lambda_tmp_file_file)
