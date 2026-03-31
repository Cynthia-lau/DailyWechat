from wechatpy import WeChatClient
import os
import json
import io
import requests
import hashlib
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

nowtime = datetime.utcnow() + timedelta(hours=8)
today = datetime.strptime(str(nowtime.date()), "%Y-%m-%d")

def get_time():
    dictDate = {'Monday': '星期一', 'Tuesday': '星期二', 'Wednesday': '星期三',
                'Thursday': '星期四', 'Friday': '星期五', 'Saturday': '星期六', 'Sunday': '星期天'}
    a = dictDate[nowtime.strftime('%A')]
    return nowtime.strftime("%Y年%m月%d日") + " " + a

def get_words():
    try:
        resp = requests.get("https://tenapi.cn/v2/yiyan?format=json", timeout=10)
        words = resp.json()
        if words.get('code') == 200:
            return words['data']['hitokoto']
    except Exception:
        pass
    return "每天都是新的开始。"

def get_weather(city, key):
    url = f"https://api.seniverse.com/v3/weather/daily.json?key={key}&location={city}&language=zh-Hans&unit=c&start=-1&days=5"
    res = requests.get(url).json()
    weather = res['results'][0]['daily'][0]
    city_name = res['results'][0]['location']['name']
    return city_name, weather

def get_count(born_date):
    delta = today - datetime.strptime(born_date, "%Y-%m-%d")
    return delta.days

def get_birthday(birthday):
    nextdate = datetime.strptime(str(today.year) + "-" + birthday, "%Y-%m-%d")
    if nextdate < today:
        nextdate = nextdate.replace(year=nextdate.year + 1)
    return (nextdate - today).days

def load_font(size):
    for path in [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "simhei.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def generate_card(data):
    W, H = 540, 740
    BG       = (255, 248, 240)
    ACCENT   = (230, 90, 80)
    DARK     = (40, 40, 40)
    GRAY     = (180, 180, 180)
    WHITE    = (255, 255, 255)
    SOFT     = (245, 235, 230)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f52 = load_font(52)
    f34 = load_font(34)
    f26 = load_font(26)
    f20 = load_font(20)

    # Header
    draw.rectangle([0, 0, W, 140], fill=ACCENT)
    draw.text((30, 22), f"Hi, {data['name']} 👋",    fill=WHITE, font=f52)
    draw.text((30, 95), data['time'],                 fill=WHITE, font=f20)

    # Weather card
    draw.rounded_rectangle([20, 158, W-20, 320], radius=16, fill=WHITE)
    draw.text((40, 172), f"📍 {data['city']}",        fill=DARK,  font=f26)
    draw.text((40, 212), f"🌤  {data['weather']}",    fill=DARK,  font=f34)
    draw.text((40, 264), f"🌡  {data['tem_low']}°C — {data['tem_high']}°C    💨 {data['wind']}",
              fill=DARK, font=f26)

    # Stats card
    draw.rounded_rectangle([20, 338, W-20, 460], radius=16, fill=WHITE)
    draw.text((40, 354), f"🎂  距生日还有  {data['birthday_left']}  天", fill=DARK, font=f26)
    draw.line([(40, 402), (W-40, 402)], fill=GRAY, width=1)
    draw.text((40, 414), f"🗓  已陪伴  {data['born_days']}  天",         fill=DARK, font=f26)

    # Quote card
    draw.rounded_rectangle([20, 478, W-20, 640], radius=16, fill=WHITE)
    draw.text((40, 492), "✨ 每日一言", fill=ACCENT, font=f26)
    draw.line([(40, 530), (W-40, 530)], fill=GRAY, width=1)
    words = data.get('words', '')
    # simple word wrap at ~18 chars
    lines, line = [], ""
    for ch in words:
        line += ch
        if len(line) >= 18:
            lines.append(line)
            line = ""
    if line:
        lines.append(line)
    y = 542
    for l in lines[:3]:
        draw.text((40, y), l, fill=DARK, font=f26)
        y += 36

    # Footer
    draw.rectangle([0, 670, W, H], fill=ACCENT)
    draw.text((30, 682), "每天都是美好的一天 🌸", fill=WHITE, font=f20)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf

def upload_image(token, img_buf):
    url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image"
    files = {"media": ("card.jpg", img_buf, "image/jpeg")}
    r = requests.post(url, files=files).json()
    print("Upload image:", r)
    return r.get("media_id")

def send_image_to_user(token, open_id, media_id):
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    payload = {
        "touser": open_id,
        "msgtype": "image",
        "image": {"media_id": media_id}
    }
    r = requests.post(url, json=payload).json()
    print("Send image:", r)
    return r

def send_template(token, open_id, template_id, data):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    payload = {
        "touser": open_id,
        "template_id": template_id,
        "data": {k: {"value": str(v)} for k, v in data.items()}
    }
    r = requests.post(url, json=payload).json()
    print("Send template:", r)
    return r

if __name__ == '__main__':
    app_id      = os.getenv("APP_ID")
    app_secret  = os.getenv("APP_SECRET")
    template_id = os.getenv("TEMPLATE_ID")
    weather_key = os.getenv("WEATHER_API_KEY")

    client = WeChatClient(app_id, app_secret)
    token  = client.fetch_access_token()['access_token']
    print(f"Token: {token[:10]}...")

    f = open("users_info.json", encoding="utf-8")
    users = json.load(f)['data']
    f.close()

    words    = get_words()
    out_time = get_time()
    print(words, out_time)

    for user_info in users:
        born_date    = user_info['born_date']
        birthday     = born_date[5:]
        city         = user_info['city']
        user_id      = user_info['user_id']
        name         = user_info['user_name'].upper()

        wea_city, weather = get_weather(city, weather_key)

        card_data = {
            'name':          name,
            'time':          out_time,
            'city':          wea_city,
            'weather':       weather['text_day'],
            'tem_high':      weather['high'],
            'tem_low':       weather['low'],
            'wind':          weather['wind_direction'],
            'born_days':     get_count(born_date),
            'birthday_left': get_birthday(birthday),
            'words':         words,
        }

        # Try sending as image card first, fall back to template
        img_buf  = generate_card(card_data)
        media_id = upload_image(token, img_buf)

        if media_id:
            result = send_image_to_user(token, user_id, media_id)
            if result.get('errcode') == 0:
                print(f"✅ Image card sent to {name}")
                continue

        # Fallback: template message
        print("Falling back to template message...")
        send_template(token, user_id, template_id, card_data)
        print(f"✅ Template message sent to {name}")
