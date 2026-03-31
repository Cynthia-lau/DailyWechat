import os
import io
import json
import base64
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

nowtime = datetime.utcnow() + timedelta(hours=8)
today   = datetime.strptime(str(nowtime.date()), "%Y-%m-%d")

REPO = "Cynthia-lau/DailyWechat"

# ── Helpers ────────────────────────────────────────────────────────

def get_time():
    days = {'Monday':'星期一','Tuesday':'星期二','Wednesday':'星期三',
            'Thursday':'星期四','Friday':'星期五','Saturday':'星期六','Sunday':'星期天'}
    return nowtime.strftime("%Y年%m月%d日") + " " + days[nowtime.strftime('%A')]

def get_words():
    try:
        r = requests.get("https://tenapi.cn/v2/yiyan?format=json", timeout=10)
        d = r.json()
        if d.get('code') == 200:
            return d['data']['hitokoto']
    except Exception:
        pass
    return "每天都是新的开始。"

def get_weather(city, key):
    url = (f"https://api.seniverse.com/v3/weather/daily.json"
           f"?key={key}&location={city}&language=zh-Hans&unit=c&start=-1&days=5")
    res = requests.get(url).json()
    w   = res['results'][0]['daily'][0]
    c   = res['results'][0]['location']['name']
    return c, w

def get_count(born_date):
    return (today - datetime.strptime(born_date, "%Y-%m-%d")).days

def get_birthday(birthday):
    nxt = datetime.strptime(str(today.year) + "-" + birthday, "%Y-%m-%d")
    if nxt < today:
        nxt = nxt.replace(year=nxt.year + 1)
    return (nxt - today).days

# ── Font ───────────────────────────────────────────────────────────

def load_font(size):
    for p in ["/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
              "simhei.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

# ── Card generator ─────────────────────────────────────────────────

def weather_emoji(text):
    if '晴' in text:  return '☀️'
    if any(k in text for k in ['多云','阴']): return '⛅'
    if '雨' in text:  return '🌧️'
    if '雪' in text:  return '❄️'
    if any(k in text for k in ['雾','霾']): return '🌫️'
    return '🌤️'

def generate_card(data):
    W, H   = 900, 480
    BG     = (250, 246, 240)
    ACCENT = (210, 75, 65)
    DARK   = (35, 35, 35)
    MID    = (100, 100, 100)
    GRAY   = (210, 210, 210)
    WHITE  = (255, 255, 255)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    f56 = load_font(56)
    f34 = load_font(34)
    f28 = load_font(28)
    f22 = load_font(22)

    draw.rectangle([0, 0, 10, H], fill=ACCENT)
    draw.text((38, 28),  f"Hi, {data['name']} 👋",  fill=ACCENT, font=f56)
    draw.text((38, 100), data['time'],                fill=MID,    font=f28)
    draw.line([(38, 148), (W-38, 148)], fill=GRAY, width=1)

    emoji = weather_emoji(data['weather'])
    draw.text((38, 162),
              f"{emoji} {data['weather']}  🌡 {data['tem_low']}°C ~ {data['tem_high']}°C  "
              f"💨 {data['wind']}  📍 {data['city']}",
              fill=DARK, font=f28)
    draw.text((38, 215),
              f"🎂 距生日还有 {data['birthday_left']} 天        🗓 已陪伴 {data['born_days']} 天",
              fill=DARK, font=f28)
    draw.line([(38, 268), (W-38, 268)], fill=GRAY, width=1)
    draw.text((38, 282), "✨ 每日一言", fill=ACCENT, font=f28)

    words, line, lines = data.get('words', ''), "", []
    for ch in words:
        line += ch
        if len(line) >= 30:
            lines.append(line); line = ""
    if line: lines.append(line)
    y = 324
    for l in lines[:2]:
        draw.text((38, y), l, fill=DARK, font=f28); y += 40

    draw.rectangle([0, H-46, W, H], fill=ACCENT)
    draw.text((38, H-34), "每天都是美好的一天 🌸", fill=WHITE, font=f22)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf

# ── GitHub image hosting ───────────────────────────────────────────

def upload_card_to_github(img_buf, token):
    path    = "daily_card.jpg"
    content = base64.b64encode(img_buf.read()).decode()
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.v3+json"}
    sha = None
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{path}",
                     headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")
    body = {"message": f"chore: daily card {nowtime.strftime('%Y-%m-%d')}",
            "content": content, "branch": "master"}
    if sha:
        body["sha"] = sha
    r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{path}",
                     json=body, headers=headers)
    print("GitHub upload:", r.status_code)
    date_str = nowtime.strftime("%Y%m%d")
    return f"https://raw.githubusercontent.com/{REPO}/master/{path}?d={date_str}"

# ── 企业微信 app message API ───────────────────────────────────────

def get_wxwork_token(corp_id, agent_secret):
    url = (f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
           f"?corpid={corp_id}&corpsecret={agent_secret}")
    r = requests.get(url).json()
    print("Token response:", r.get('errmsg'), r.get('expires_in'))
    return r['access_token']

def send_news_card(token, agent_id, user_id, data, pic_url):
    title = (f"{data['time']}  |  "
             f"{weather_emoji(data['weather'])} {data['weather']} "
             f"{data['tem_low']}~{data['tem_high']}°C  📍{data['city']}")
    desc  = (f"💨 {data['wind']}\n"
             f"🎂 距生日还有 {data['birthday_left']} 天  |  🗓 已陪伴 {data['born_days']} 天\n"
             f"✨ {data['words']}")

    payload = {
        "touser":  user_id,
        "msgtype": "news",
        "agentid": int(agent_id),
        "news": {"articles": [{
            "title":       title,
            "description": desc,
            "url":         "https://github.com/Cynthia-lau/DailyWechat",
            "picurl":      pic_url
        }]}
    }
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    r   = requests.post(url, json=payload).json()
    print("Send result:", r)
    return r

# ── Main ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    corp_id      = os.getenv("CORP_ID")
    agent_id     = os.getenv("AGENT_ID")
    agent_secret = os.getenv("AGENT_SECRET")
    user_id      = os.getenv("USER_ID")
    weather_key  = os.getenv("WEATHER_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    wxwork_token = get_wxwork_token(corp_id, agent_secret)

    f     = open("users_info.json", encoding="utf-8")
    users = json.load(f)['data']
    f.close()

    words    = get_words()
    out_time = get_time()
    print(f"Time: {out_time} | Quote: {words}")

    for user_info in users:
        born_date = user_info['born_date']
        city      = user_info['city']
        name      = user_info['user_name'].upper()

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
            'birthday_left': get_birthday(born_date[5:]),
            'words':         words,
        }

        print(f"Generating card for {name}...")
        img_buf  = generate_card(card_data)
        pic_url  = upload_card_to_github(img_buf, github_token)
        print(f"Card URL: {pic_url}")

        result = send_news_card(wxwork_token, agent_id, user_id, card_data, pic_url)
        if result.get('errcode') == 0:
            print(f"✅ News card sent to {name}")
        else:
            print(f"❌ Failed: {result}")
