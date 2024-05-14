# ToDAM Line Bot with Lambda Functions

Develop a Line bot using AWS Lambda Functions and `linebot.v3` library, utilizing `Python 3.12` runtime. 

> [!IMPORTANT]
> Note that `Python 3.12` operates on an **Amazon Linux 2023 Amazon Machine Image (AMI)**. Hence, ensure the creation of the layer on an **Amazon Linux 2023 OS**. [^3]

## Create `Lambda Function` Layer

### Create `line-bot-sdk` Layer [^3]

```shell
$ mkdir -p lambda-layer/python
$ cd lambda-layer/python
$ pip3 install --platform manylinux2014_x86_64 --target . --python-version 3.12 --only-binary=:all: line-bot-sdk
$ cd ..
$ zip -r linebot_lambda_layer.zip python
```

### Create `dotenv` Layer [^3]

```shell
$ mkdir -p lambda-layer/python
$ cd lambda-layer/python
$ pip3 install --platform manylinux2014_x86_64 --target . --python-version 3.12 --only-binary=:all: python-dotenv
$ cd ..
$ zip -r dotenv_lambda_layer.zip python
```

## Add Permission with s3 [^2]
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AddPerm",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": [
                "arn:aws:s3:::<your-bucket-name>",
                "arn:aws:s3:::<your-bucket-name>/*"
            ]
        }
    ]
}
```

## Project Structure

```shell
todam-lambda-function-linebot/
├── lambda_function.py
├── LICENSE
├── poetry.lock
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Functions and Features

### Import Libraries

import the necessary libraries and set up the environment variables.

```python
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

aws_region_name = os.environ["AWS_CLIENT_REGION_NAME"]
aws_bucket_name = os.environ["AWS_CLIENT_BUCKET_NAME"]
```

### Create the `s3_client` object

create the `s3_client` object to interact with the S3 bucket.

```python
s3_client = boto3.client(
    "s3",
    region_name=aws_region_name
)
```

### Handle the different types of messages

Handle the different types of messages, including text, sticker, image, video, and audio messages.


#### Text Message

```python
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    """
    Only handle the text message event, but do nothing.

    In the future, we may add the model to check the message
    explicitly or not, and then suggest the user to resend the message.
    """
    ...
    return
```

> [!NOTE]
> Once we need to send the message to the user, we have to add the content that we want to reply before `handle_message` function returns.
>
> examples:
> 
> ```python
> with ApiClient(configuration) as api_client:
>     line_bot_api = MessagingApi(api_client)
>     line_bot_api.show_loading_animation(
>         ShowLoadingAnimationRequest(
>             chat_id=event.source.user_id,
>         )
>     )
>     # Add the content that we want to reply before the function returns
>     reply_messages = [
>         TextMessage("DAMMMM 蟹 Bro, M3 換一句試試吧！"),
>         TextMessage("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
>         TextMessage(f"Time elapsed: {time.time() - start_time} seconds.")
>     ]
> 
>     line_bot_api.reply_message_with_http_info(
>         ReplyMessageRequest(
>             reply_token=event.reply_token,
>             messages=reply_messages,
>         )
>     )
> ```

#### Sticker Message

```python
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
                messages=[TextMessage(text="$", emojis=[{"index": 0, "productId": "5ac21c46040ab15980c9b442", "emojiId": "138"}])]  # We can change the different sticker here
            )
        )
```


#### Image, Video, and Audio Messages

```python
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
```

Store the user uploaded image, video, or audio to the S3 bucket.

```python
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
```


### Lambda Handler

Handle the webhook event and store the user log to the S3 bucket.

```python
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
```

#### User Log

Store the user log to the S3 bucket.

```python
@staticmethod
def store_user_log(body: str) -> None:
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")

    s3_goal_file_path = f"{current_time}.log"
    lambda_tmp_file_file = "/tmp/events.log"

    with open(lambda_tmp_file_file, "a", encoding="utf-8") as f:
        f.write(f"{body}\n")
    s3_client.upload_file(lambda_tmp_file_file, aws_bucket_name, s3_goal_file_path)
    os.remove(lambda_tmp_file_file)
```


[^1]: [使用 .zip 封存檔部署 Python Lambda 函數](https://docs.aws.amazon.com/zh_tw/lambda/latest/dg/python-package.html)
[^2]: [Policies and Permissions in Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-policy-language-overview.html?icmpid=docs_amazons3_console)
[^3]: [How do I resolve the "Unable to import module" error that I receive when I run Lambda code in Python?](https://repost.aws/knowledge-center/lambda-import-module-error-python)

