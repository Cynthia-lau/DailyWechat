import os
import io
import requests
from PIL import Image, ImageDraw, ImageFont

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
OPEN_ID = os.getenv("OPEN_ID")  # we'll add this secret

def get_access_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    r = requests.get(url).json()
    print("Access token response:", r)
    return r.get("access_token")

def create_test_image():
    """Create a small solid-color test image in memory."""
    img = Image.new("RGB", (200, 100), color=(255, 140, 80))
    draw = ImageDraw.Draw(img)
    draw.text((20, 35), "Test Image", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def upload_image(token, img_buf):
    """Upload image as temporary media."""
    url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image"
    files = {"media": ("test.png", img_buf, "image/png")}
    r = requests.post(url, files=files).json()
    print("Upload response:", r)
    return r.get("media_id")

def send_image_message(token, open_id, media_id):
    """Send image via customer service (kefu) message API."""
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    payload = {
        "touser": open_id,
        "msgtype": "image",
        "image": {"media_id": media_id}
    }
    r = requests.post(url, json=payload).json()
    print("Send image response:", r)
    return r

if __name__ == "__main__":
    print("=== Testing image send capability ===")
    print(f"APP_ID: {APP_ID}")
    print(f"OPEN_ID: {OPEN_ID}")

    token = get_access_token()
    if not token:
        print("FAILED: Could not get access token")
        exit(1)

    print(f"Got token: {token[:10]}...")

    img_buf = create_test_image()
    media_id = upload_image(token, img_buf)
    if not media_id:
        print("FAILED: Could not upload image - account may not support media upload")
        exit(1)

    print(f"Got media_id: {media_id}")

    result = send_image_message(token, OPEN_ID, media_id)
    if result.get("errcode") == 0:
        print("SUCCESS: Image message sent!")
    else:
        print(f"FAILED to send: errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")
