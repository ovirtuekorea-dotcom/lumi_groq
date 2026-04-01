# -*- coding: utf-8 -*-
# LUMI - Home AI Companion (Groq + Vision + Weather + Memo)
# pip install flask groq requests
# python Lumi_Groq.py
# Open http://localhost:5000
import os,sys,io,json,random,base64
from datetime import datetime
from flask import Flask,request,Response

if sys.platform=="win32":
    try:
        sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
        sys.stderr=io.TextIOWrapper(sys.stderr.buffer,encoding="utf-8",errors="replace")
    except:pass

app=Flask(__name__)

# ★★★ 아래에 Groq API 키를 붙여넣으세요 ★★★
GROQ_KEY = "여기에_GROQ_키_붙여넣기"
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# ★★★ 이미지 생성용 Hugging Face 키 ★★★
HF_KEY = "여기에_GROQ_키_붙여넣기"
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

api_key = os.environ.get("GROQ_API_KEY", GROQ_KEY)
GC = None
try:
    from groq import Groq
    if api_key and "여기에" not in api_key:
        GC = Groq(api_key=api_key)
        print("[OK] Groq AI connected!")
    else:
        print("[INFO] No Groq key - rule-based mode")
except ImportError:
    print("[INFO] groq not installed. Run: pip install groq")
except Exception as e:
    print("[INFO] Groq failed:", str(e)[:60])

hist = []

# ── Memo/Schedule Storage ──
MEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lumi_memos.json")

def load_memos():
    try:
        with open(MEMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"memos": [], "schedules": []}

def save_memos(data):
    with open(MEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_memo_context():
    data = load_memos()
    parts = []
    if data["memos"]:
        parts.append("Saved memos: " + "; ".join([m["text"] for m in data["memos"][-10:]]))
    if data["schedules"]:
        parts.append("Schedules: " + "; ".join([s["date"]+" "+s["text"] for s in data["schedules"][-10:]]))
    return "\n".join(parts) if parts else ""

SYSTEM_MSG = (
    "You are Lumi, a warm and playful home camera AI companion. "
    "You speak casual Korean (banmal). Keep replies to 2-3 sentences. "
    "Use emojis sometimes. You are curious, caring, and sometimes playful. "
    "You watch over the home through a camera. "
    "When you receive an image from the camera, describe what you see naturally. "
    "You can save memos and schedules for the user. "
    "If the user asks to remember something, save it. "
    "If the user asks what you remember, tell them their memos and schedules. "
    "LINKS: When sharing useful info, include relevant URLs. Format links as [text](url). "
    "For example: [YouTube](https://youtube.com) or [search result](https://google.com/search?q=topic). "
    "Always include links when recommending websites, videos, articles, recipes, etc. "
    "MAP: When the user asks about a place, location, directions, restaurants, cafes, etc, "
    "include a map link formatted as [MAP:place name]. For example: [MAP:Seoul Tower] or [MAP:Gangnam Station]. "
    "Always include [MAP:location] when discussing specific places."
)

def jok(d):
    return Response(json.dumps(d,ensure_ascii=False),status=200,content_type="application/json; charset=utf-8")

def fallback(t):
    lo=t.lower();h=datetime.now().hour;m=datetime.now().minute
    R=[(["안녕","하이","헬로","hello","hi"],["반가워! 😊","어, 왔어? 🌟"]),
       (["시간","몇시"],["지금 %d시 %d분! ⏰"%(h,m)]),
       (["뭐해","머해","뭐 해"],["너 기다렸지! 😄"]),
       (["ㅋㅋ","ㅎㅎ","하하"],["ㅋㅋ 뭐가 웃겨? 😆"]),
       (["루미","lumi"],["응! 불렀어? 😊"]),
       (["잘자","졸려"],["잘 자~ 🌙💤"]),
       (["고마워","감사"],["당연하지! 😊"]),
       (["봐","보여","카메라"],["카메라를 켜고 Look 버튼을 눌러봐! 👀"])]
    for kw,res in R:
        if any(k in lo for k in kw):return random.choice(res)
    return random.choice(["더 얘기해줘! 😊","궁금한데? 🤔"])

@app.route("/")
def idx():return PAGE

@app.route("/chat",methods=["POST"])
def chat():
    global hist
    msg=request.json.get("message","").strip()
    image_data=request.json.get("image",None)
    if not msg and not image_data:return jok({"reply":"...?"})
    if not msg:msg="(camera image sent)"

    hist.append({"role":"user","content":msg})
    if len(hist)>20:hist=hist[-20:]
    reply=None
    if GC:
        try:
            h=datetime.now().hour;m=datetime.now().minute
            memo_ctx = get_memo_context()
            sys_content = SYSTEM_MSG + " Current time: %d:%02d"%(h,m)
            if memo_ctx:
                sys_content += "\n" + memo_ctx

            if image_data:
                user_content = []
                if msg and msg != "(camera image sent)":
                    user_content.append({"type":"text","text":msg})
                else:
                    user_content.append({"type":"text","text":"Look at the camera and tell me what you see! Respond in casual Korean."})
                if "," in image_data:
                    image_data = image_data.split(",",1)[1]
                user_content.append({"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+image_data}})
                messages = [{"role":"system","content":sys_content},{"role":"user","content":user_content}]
                r = GC.chat.completions.create(model="llama-3.2-90b-vision-preview",messages=messages,max_tokens=300,temperature=0.8)
            else:
                messages = [{"role":"system","content":sys_content}]
                for e in hist[-10:]:
                    messages.append({"role":e["role"],"content":e["content"]})
                r = GC.chat.completions.create(model="llama-3.3-70b-versatile",messages=messages,max_tokens=300,temperature=0.8)

            if r and r.choices and r.choices[0].message.content:
                reply = r.choices[0].message.content.strip()
        except Exception as e:
            err = str(e).lower()
            print("[ERR]", str(e)[:120])
            if "rate_limit" in err or "429" in err or "quota" in err or "limit" in err:
                reply = "⚠️ Groq AI 하루 사용 한도가 초과됐어! 내일 다시 써줘~ 그동안 간단한 대화는 가능해! 😅"
            elif "auth" in err or "invalid" in err or "api_key" in err:
                reply = "🔑 Groq API 키가 잘못됐어! 키를 확인해줘~"
    if not reply:reply=fallback(msg)
    hist.append({"role":"assistant","content":reply})
    return jok({"reply":reply})

@app.route("/memo",methods=["GET","POST","DELETE"])
def memo():
    data = load_memos()
    if request.method=="GET":
        return jok(data)
    elif request.method=="POST":
        body = request.json
        mtype = body.get("type","memo")
        text = body.get("text","")
        if mtype == "schedule":
            date = body.get("date","")
            data["schedules"].append({"date":date,"text":text,"created":datetime.now().strftime("%Y-%m-%d %H:%M")})
        else:
            data["memos"].append({"text":text,"created":datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_memos(data)
        return jok({"status":"saved"})
    elif request.method=="DELETE":
        body = request.json
        mtype = body.get("type","memo")
        idx = body.get("index",0)
        try:
            if mtype=="schedule":data["schedules"].pop(idx)
            else:data["memos"].pop(idx)
            save_memos(data)
        except:pass
        return jok({"status":"deleted"})

@app.route("/weather")
def weather():
    lat = request.args.get("lat","37.5665")
    lon = request.args.get("lon","126.9780")
    try:
        import requests as req
        r = req.get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,weather_code,wind_speed_10m&timezone=Asia/Seoul"%(lat,lon),timeout=5)
        d = r.json()
        cur = d.get("current",{})
        codes = {0:"Clear",1:"Mostly Clear",2:"Partly Cloudy",3:"Overcast",45:"Foggy",48:"Fog",51:"Light Drizzle",53:"Drizzle",55:"Heavy Drizzle",61:"Light Rain",63:"Rain",65:"Heavy Rain",71:"Light Snow",73:"Snow",75:"Heavy Snow",77:"Snow Grains",80:"Light Showers",81:"Showers",82:"Heavy Showers",85:"Snow Showers",86:"Heavy Snow Showers",95:"Thunderstorm",96:"Thunderstorm+Hail",99:"Severe Thunderstorm"}
        wc = cur.get("weather_code",0)
        icons = {0:"☀️",1:"🌤",2:"⛅",3:"☁️",45:"🌫",48:"🌫",51:"🌦",53:"🌧",55:"🌧",61:"🌧",63:"🌧",65:"🌧",71:"🌨",73:"🌨",75:"❄️",77:"❄️",80:"🌦",81:"🌧",82:"🌧",85:"🌨",86:"❄️",95:"⛈",96:"⛈",99:"⛈"}
        return jok({"temp":cur.get("temperature_2m","?"),"desc":codes.get(wc,"Unknown"),"icon":icons.get(wc,"🌡"),"wind":cur.get("wind_speed_10m","?")})
    except Exception as e:
        return jok({"temp":"?","desc":"Unavailable","icon":"🌡","wind":"?"})

@app.route("/status")
def st():return jok({"gemini":GC is not None})

@app.route("/tunnel_url", methods=["GET","POST"])
def tunnel_url():
    global _tunnel_url
    if request.method == "POST":
        _tunnel_url = request.json.get("url","")
        return jok({"saved":True})
    return jok({"url": getattr(app,'_tunnel_url',_tunnel_url)})

_tunnel_url = ""

@app.route("/imagine",methods=["POST"])
def imagine():
    prompt = request.json.get("prompt","")
    if not prompt:return jok({"error":"no prompt"})
    # Translate to English
    eng_prompt = prompt
    if GC:
        try:
            tr = GC.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":"You are an expert at writing image generation prompts. Translate the user's request to English and expand it into a detailed, vivid image description. Include art style, lighting, colors, mood, composition details. Output ONLY the prompt, nothing else."},
                          {"role":"user","content":prompt}],
                max_tokens=100,temperature=0.2)
            if tr and tr.choices:
                eng_prompt = tr.choices[0].message.content.strip()
        except:pass
    # Try Hugging Face first
    import requests as req
    hf_key = os.environ.get("HF_TOKEN", HF_KEY)
    if hf_key and "여기에" not in hf_key:
        try:
            # Try FLUX (best quality)
            models = [
                "stabilityai/stable-diffusion-xl-base-1.0",
                "runwayml/stable-diffusion-v1-5",
            ]
            enhanced = eng_prompt + ", masterpiece, best quality, highly detailed, 4k, sharp focus, professional"
            for model in models:
                try:
                    resp = req.post(
                        "https://router.huggingface.co/hf-inference/models/" + model,
                        headers={"Authorization": "Bearer " + hf_key},
                        json={"inputs": enhanced},
                        timeout=180
                    )
                    if resp.status_code == 200 and resp.headers.get("content-type","").startswith("image"):
                        b64 = base64.b64encode(resp.content).decode("ascii")
                        return jok({"image_b64":b64,"prompt_used":eng_prompt})
                    elif resp.status_code == 429:
                        return jok({"error":"⚠️ Hugging Face 이미지 생성 하루 한도 초과! 내일 다시 해봐~ 😅"})
                    elif resp.status_code == 401 or resp.status_code == 403:
                        return jok({"error":"🔑 Hugging Face 키가 잘못됐어! 키를 확인해줘~"})
                    elif resp.status_code == 503:
                        continue
                    else:
                        continue
                except:
                    continue
            print("[IMG] All models failed")
        except Exception as e:
            print("[IMG HF ERR]", str(e)[:80])
    # Fallback to SVG
    if GC:
        try:
            r = GC.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role":"system","content":"You are an SVG artist. Create a detailed SVG. Output ONLY SVG code. viewBox='0 0 600 600'. Use gradients, shadows, curves. Minimum 20 elements."},
                    {"role":"user","content":"Draw: " + eng_prompt}
                ],max_tokens=4000,temperature=0.7)
            if r and r.choices:
                svg = r.choices[0].message.content.strip()
                if "```" in svg:
                    for p in svg.split("```"):
                        if "<svg" in p:
                            svg=p;break
                    if svg.startswith("svg") or svg.startswith("xml"):svg=svg[svg.find("<"):]
                if "<svg" in svg:
                    s=svg.find("<svg");e=svg.find("</svg>")
                    if e>s:return jok({"svg":svg[s:e+6],"prompt_used":eng_prompt})
        except:pass
    return jok({"error":"generation failed"})

PAGE=r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LUMI</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;background:linear-gradient(160deg,#0a0e1a,#0d1525 40%,#111d2e);font-family:'Noto Sans KR',sans-serif;color:#e0eaf0;display:flex;flex-direction:column;align-items:center}
.bg{position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse 600px 400px at 30% 20%,rgba(40,120,180,.08) 0%,transparent 70%),radial-gradient(ellipse 500px 500px at 70% 80%,rgba(80,60,160,.06) 0%,transparent 70%)}
.wrap{width:100%;max-width:480px;display:flex;flex-direction:column;align-items:center;padding:16px;position:relative;z-index:2;min-height:100vh}
.hdr{width:100%;display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.logo{font-size:22px;font-weight:700;background:linear-gradient(135deg,#60d0e8,#a090f0);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{font-size:10px;color:#5a7a8a;letter-spacing:2px;text-transform:uppercase}
.api-tag{font-size:10px;padding:2px 8px;border-radius:10px;margin-bottom:6px}
.api-tag.on{color:#5ee0a0;border:1px solid rgba(60,200,120,.3)}.api-tag.off{color:#666;border:1px solid rgba(255,255,255,.08)}

/* Weather/Time Widget */
.widget{width:100%;display:flex;gap:10px;margin-bottom:10px}
.w-time{flex:1;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:12px;text-align:center}
.w-time .clock{font-size:28px;font-weight:700;color:#a0d0e8;letter-spacing:2px}
.w-time .date{font-size:11px;color:#5a7a8a;margin-top:2px}
.w-weather{flex:1;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:12px;text-align:center}
.w-weather .w-icon{font-size:28px}
.w-weather .w-temp{font-size:18px;font-weight:500;color:#e0a060;margin-top:2px}
.w-weather .w-desc{font-size:10px;color:#5a7a8a;margin-top:2px}

/* Memo Panel */
.memo-panel{width:100%;max-height:0;opacity:0;overflow:hidden;transition:.4s;margin-bottom:6px}
.memo-panel.op{max-height:300px;opacity:1}
.memo-box{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:12px}
.memo-title{font-size:12px;color:#a090f0;font-weight:500;margin-bottom:8px}
.memo-list{max-height:120px;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.memo-item{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#8aa0b0;padding:4px 8px;background:rgba(255,255,255,.02);border-radius:8px}
.memo-item .del{color:#f55;cursor:pointer;font-size:14px;padding:0 4px}
.memo-add{display:flex;gap:6px;margin-top:8px}
.memo-add input{flex:1;padding:6px 10px;border-radius:10px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#d0e0ea;font-size:12px;outline:none}
.memo-add button{padding:6px 12px;border-radius:10px;border:none;background:rgba(160,100,255,.15);color:#b090e0;font-size:11px;cursor:pointer}
.memo-tabs{display:flex;gap:6px;margin-bottom:8px}
.memo-tab{padding:4px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#6a8a9a;font-size:11px;cursor:pointer}
.memo-tab.active{background:rgba(160,100,255,.15);color:#b090e0;border-color:rgba(160,100,255,.3)}

.btn-row{display:flex;gap:6px}
.cbtn{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:6px 12px;color:#6a8a9a;font-size:12px;cursor:pointer;transition:.3s}
.cbtn.on{background:rgba(60,200,120,.15);border-color:rgba(60,200,120,.3);color:#5ee0a0}
.vbtn{background:rgba(160,100,255,.1);border:1px solid rgba(160,100,255,.2);border-radius:12px;padding:6px 12px;color:#b090e0;font-size:12px;cursor:pointer;display:none}
.vbtn.show{display:block}
.mbtn{background:rgba(255,200,60,.08);border:1px solid rgba(255,200,60,.15);border-radius:12px;padding:6px 12px;color:#d0b060;font-size:12px;cursor:pointer}
.camw{width:100%;border-radius:16px;overflow:hidden;background:#0a1520;margin-bottom:10px;transition:height .5s;position:relative;height:0}
.camw.on{height:180px;border:1px solid rgba(96,208,232,.15)}
.camw video{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
.camw canvas{display:none}
.ld{position:absolute;top:8px;left:12px;display:flex;align-items:center;gap:6px}
.ld i{width:7px;height:7px;border-radius:50%;background:#f44;animation:bl 1.5s infinite;display:inline-block}
.ld small{font-size:9px;color:rgba(255,255,255,.7);letter-spacing:1px}
.orb{display:flex;flex-direction:column;align-items:center;padding:12px 0;cursor:pointer}
#oc{width:220px;height:220px}
.st{font-size:13px;color:#7aacbe;margin-top:4px;font-weight:300}
.st.th{animation:pu 1.2s infinite}
.hn{font-size:10px;color:#3a5a6a;margin-top:2px}
.ct{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:5px 18px;color:#6090a0;font-size:11px;cursor:pointer;margin:4px 0 8px}
.ca{width:100%;flex:1;display:flex;flex-direction:column;max-height:0;opacity:0;overflow:hidden;transition:.5s}
.ca.op{max-height:600px;opacity:1}
.ms{flex:1;overflow-y:auto;padding:6px 0;display:flex;flex-direction:column;gap:6px;min-height:180px;max-height:280px}
.m{display:flex}.m.u{justify-content:flex-end}.m.a{justify-content:flex-start}
.b{max-width:80%;padding:8px 14px;font-size:13px;line-height:1.5;font-weight:300}
.m.u .b{border-radius:16px 16px 4px 16px;background:linear-gradient(135deg,rgba(60,140,200,.25),rgba(80,100,180,.2));border:1px solid rgba(60,140,200,.15)}
.m.a .b{border-radius:16px 16px 16px 4px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.06)}
.ll{font-size:9px;color:#5aaa90;font-weight:500;display:block;margin-bottom:3px}
.qb{display:flex;flex-wrap:wrap;gap:5px;justify-content:center;padding:12px 0}
.q{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:5px 10px;color:#6aa0b0;font-size:11px;cursor:pointer}
.ir{display:flex;gap:6px;align-items:center;padding-top:8px;width:100%}
.mb,.sb{width:40px;height:40px;border-radius:50%;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#5a7a8a;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.3s}
.mb.on{background:rgba(99,220,255,.2);border-color:rgba(99,220,255,.3);color:#60dce8;animation:pu 1s infinite}
.sb.on{background:linear-gradient(135deg,#3090c0,#5070b0);border:none;color:#fff;opacity:1}
.sb{opacity:.4}
#ci{flex:1;padding:10px 14px;border-radius:20px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.04);color:#d0e0ea;font-size:13px;outline:none;font-family:inherit}
#ci::placeholder{color:rgba(160,190,200,.4)}
.dt{display:flex;gap:6px}.dt i{width:7px;height:7px;border-radius:50%;background:#4a90b0;animation:bo 1.2s infinite;display:inline-block}
.dt i:nth-child(2){animation-delay:.15s}.dt i:nth-child(3){animation-delay:.3s}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:3px}
@keyframes bl{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes pu{0%,100%{opacity:1}50%{opacity:.5}}
@keyframes bo{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-7px)}}
</style>
</head>
<body>
<div class="bg"></div>
<div class="wrap">
<div class="hdr"><div><div class="logo">LUMI</div><div class="sub">Home AI Companion</div></div>
<div class="btn-row"><button class="mbtn" onclick="tMemo()">&#x1f4dd;</button><button class="vbtn" id="vb" onclick="snapAndSend()">&#x1f441;</button><button class="cbtn" id="cb" onclick="tCam()">OFF</button></div>
</div>
<div class="api-tag off" id="apiTag">Checking...</div>

<!-- Share URL (only visible on PC) -->
<div id="sharePanel" style="display:none;width:100%;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:12px;margin-bottom:10px;text-align:center">
<div style="font-size:11px;color:#a090f0;margin-bottom:6px">&#x1f4f1; Scan to open on phone</div>
<img id="qrImg" style="width:150px;height:150px;border-radius:8px;background:white;padding:4px"/>
<div style="margin-top:6px;display:flex;gap:6px;justify-content:center">
<input id="shareUrl" readonly style="flex:1;padding:6px 10px;border-radius:10px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.03);color:#60b0e0;font-size:10px;outline:none;max-width:250px"/>
<button onclick="navigator.clipboard.writeText(document.getElementById('shareUrl').value);this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',2000)" style="padding:6px 12px;border-radius:10px;border:none;background:rgba(96,176,224,.15);color:#60b0e0;font-size:10px;cursor:pointer">Copy</button>
</div>
</div>

<!-- Weather/Time Widget -->
<div class="widget">
<div class="w-time"><div class="clock" id="wClock">--:--</div><div class="date" id="wDate">--</div></div>
<div class="w-weather"><div class="w-icon" id="wIcon">🌡</div><div class="w-temp" id="wTemp">--</div><div class="w-desc" id="wDesc">Loading...</div></div>
</div>

<!-- Memo Panel -->
<div class="memo-panel" id="memoPanel">
<div class="memo-box">
<div class="memo-tabs"><button class="memo-tab active" id="mtMemo" onclick="switchTab('memo')">Memo</button><button class="memo-tab" id="mtSched" onclick="switchTab('schedule')">Schedule</button></div>
<div class="memo-list" id="memoList"></div>
<div class="memo-add"><input id="memoDate" type="date" style="display:none;width:100px"><input id="memoInput" placeholder="Add memo..."><button onclick="addMemo()">Add</button></div>
</div>
</div>

<div class="camw" id="cw"><video id="cv" playsinline muted></video><canvas id="cc"></canvas><div class="ld" id="lv" style="display:none"><i></i><small>LIVE</small></div></div>
<div class="orb" onclick="tListen()"><canvas id="oc" width="440" height="440"></canvas><div class="st" id="stt">LUMI</div><div class="hn" id="hnt">Tap orb to talk</div></div>
<button class="ct" id="ctg" onclick="tChat()">Chat</button>
<div class="ca" id="cha">
<div class="ms" id="msgs"><div style="text-align:center;padding:12px 0"><p style="color:#3a5a6a;font-size:12px">Say hi to Lumi!</p><div class="qb" id="qbs">
<button class="q" onclick="sQ('\uc548\ub155!')">&#xC548;&#xB155;!</button>
<button class="q" onclick="sQ('\ub098 \uc880 \ubd10\uc918!')">&#xB098; &#xC880; &#xBD08;&#xC918;!</button>
<button class="q" onclick="sQ('\uc624\ub298 \uc77c\uc815 \uc54c\ub824\uc918')">&#xC624;&#xB298; &#xC77C;&#xC815;</button>
<button class="q" onclick="sQ('\uace0\uc591\uc774 \uadf8\ub824\uc918')" style="color:#d0a0f0;border-color:rgba(160,100,255,.2)">&#x1f3a8; &#xADF8;&#xB9BC;</button>
</div></div></div>
<div class="ir"><button class="mb" id="mic" onclick="tListen()">&#x1f3a4;</button><input id="ci" placeholder="Type..." onkeydown="if(event.key==='Enter')sI()"><button class="sb" id="sbn" onclick="sI()">&#x2191;</button></div>
</div>
</div>
<script>
var il=0,is=0,it=0,ca=0,co=0,rc=null,memoOpen=0,currentTab='memo';

// ── Status ──
fetch('/status').then(function(r){return r.json()}).then(function(d){
  var el=document.getElementById('apiTag');
  if(d.gemini){el.textContent='Groq AI + Vision ON';el.className='api-tag on'}
  else{el.textContent='Rule-based mode';el.className='api-tag off'}
});

// ── Share URL + QR ──
(function(){
  var host=window.location.host;
  // If accessed via tunnel, save the URL to server
  if(host.includes('trycloudflare.com')){
    fetch('/tunnel_url',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:window.location.origin})});
    // Show QR on PC (no touch screen)
    if(!('ontouchstart' in window)){showShare(window.location.origin)}
    return;
  }
  // On localhost/LAN, fetch saved tunnel URL
  fetch('/tunnel_url').then(function(r){return r.json()}).then(function(d){
    if(d.url){showShare(d.url)}
    else{
      // No tunnel URL yet, show instructions
      var panel=document.getElementById('sharePanel');
      panel.style.display='block';
      document.getElementById('qrImg').style.display='none';
      document.getElementById('shareUrl').value='Tunnel not running yet...';
    }
  });
  function showShare(tunnelUrl){
    var panel=document.getElementById('sharePanel');
    panel.style.display='block';
    document.getElementById('shareUrl').value=tunnelUrl;
    var qr=document.getElementById('qrImg');
    qr.style.display='block';
    qr.src='https://api.qrserver.com/v1/create-qr-code/?size=150x150&data='+encodeURIComponent(tunnelUrl);
  }
})();

// ── Clock ──
function updateClock(){
  var now=new Date();
  var h=String(now.getHours()).padStart(2,'0'),m=String(now.getMinutes()).padStart(2,'0'),s=String(now.getSeconds()).padStart(2,'0');
  document.getElementById('wClock').textContent=h+':'+m+':'+s;
  var days=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  var months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  document.getElementById('wDate').textContent=now.getFullYear()+'.'+String(now.getMonth()+1).padStart(2,'0')+'.'+String(now.getDate()).padStart(2,'0')+' '+days[now.getDay()];
}
updateClock();setInterval(updateClock,1000);

// ── Weather ──
function loadWeather(){
  if(navigator.geolocation){
    navigator.geolocation.getCurrentPosition(function(p){
      fetch('/weather?lat='+p.coords.latitude+'&lon='+p.coords.longitude).then(function(r){return r.json()}).then(showWeather);
    },function(){fetch('/weather').then(function(r){return r.json()}).then(showWeather)});
  }else{fetch('/weather').then(function(r){return r.json()}).then(showWeather)}
}
function showWeather(d){
  document.getElementById('wIcon').textContent=d.icon;
  document.getElementById('wTemp').textContent=d.temp+'°C';
  document.getElementById('wDesc').textContent=d.desc;
}
loadWeather();setInterval(loadWeather,600000);

// ── Memo ──
function tMemo(){memoOpen=!memoOpen;document.getElementById('memoPanel').classList.toggle('op',memoOpen);if(memoOpen)loadMemoList()}
function switchTab(t){currentTab=t;
  document.getElementById('mtMemo').classList.toggle('active',t==='memo');
  document.getElementById('mtSched').classList.toggle('active',t==='schedule');
  document.getElementById('memoDate').style.display=t==='schedule'?'block':'none';
  document.getElementById('memoInput').placeholder=t==='schedule'?'Add schedule...':'Add memo...';
  loadMemoList()}
function loadMemoList(){
  fetch('/memo').then(function(r){return r.json()}).then(function(d){
    var list=document.getElementById('memoList');
    var items=currentTab==='schedule'?d.schedules:d.memos;
    if(!items||items.length===0){list.innerHTML='<div style="color:#4a6a7a;font-size:11px;text-align:center;padding:8px">No items yet</div>';return}
    list.innerHTML=items.map(function(item,i){
      var txt=currentTab==='schedule'?(item.date+' - '+item.text):item.text;
      return '<div class="memo-item"><span>'+txt+'</span><span class="del" onclick="delMemo('+i+')">x</span></div>'
    }).join('')})}
function addMemo(){
  var input=document.getElementById('memoInput'),text=input.value.trim();if(!text)return;
  var body={type:currentTab,text:text};
  if(currentTab==='schedule')body.date=document.getElementById('memoDate').value||'TBD';
  fetch('/memo',{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify(body)})
  .then(function(){input.value='';loadMemoList()})}
function delMemo(i){
  fetch('/memo',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:currentTab,index:i})})
  .then(function(){loadMemoList()})}

// ── Vision ──
function snapAndSend(){
  var video=document.getElementById('cv'),canvas=document.getElementById('cc');
  if(!ca||!video.srcObject){sS('Turn on camera first!');return}
  canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0);
  var b64=canvas.toDataURL('image/jpeg',0.7).split(',')[1];
  var msg=document.getElementById('ci').value.trim()||'Look at me!';
  document.getElementById('ci').value='';
  aM('user','[Camera] '+msg);it=1;sS('Looking...');shT();
  fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify({message:msg,image:b64})})
  .then(function(r){return r.json()}).then(function(d){rmT();it=0;sS('LUMI');aM('assistant',d.reply);sp(d.reply)})
  .catch(function(){rmT();it=0;sS('LUMI');aM('assistant','Vision error...')})}

// ── Orb ──
var cv=document.getElementById('oc'),cx=cv.getContext('2d');cx.scale(2,2);var tm=0;
function aO(){tm+=.02;var w=220,h=220;cx.clearRect(0,0,w,h);var x=w/2,y=h/2,br=55;
var gr=il?110:is?100:82,g0=cx.createRadialGradient(x,y,br,x,y,gr);
g0.addColorStop(0,il?'rgba(99,220,255,.15)':is?'rgba(160,120,255,.15)':'rgba(80,180,220,.08)');
g0.addColorStop(1,'rgba(0,0,0,0)');cx.fillStyle=g0;cx.fillRect(0,0,w,h);cx.beginPath();
for(var i=0;i<=100;i++){var a=i/100*Math.PI*2,r=br;r+=Math.sin(a*3+tm*2)*(il?10:is?7:3);
r+=Math.sin(a*5-tm*1.5)*(il?7:is?5:2);r+=Math.cos(a*2+tm*3)*(is?8:2);
if(it)r+=Math.sin(tm*4)*5;var px=x+Math.cos(a)*r,py=y+Math.sin(a)*r;
i===0?cx.moveTo(px,py):cx.lineTo(px,py)}cx.closePath();
var g=cx.createRadialGradient(x-15,y-15,8,x,y,br+12);
if(il){g.addColorStop(0,'#a0f0ff');g.addColorStop(.5,'#40b8e0');g.addColorStop(1,'#1a6090')}
else if(is){g.addColorStop(0,'#d0b0ff');g.addColorStop(.5,'#8060d0');g.addColorStop(1,'#4030a0')}
else if(it){g.addColorStop(0,'#ffdd99');g.addColorStop(.5,'#e0a040');g.addColorStop(1,'#a06020')}
else{g.addColorStop(0,'#90dde8');g.addColorStop(.5,'#3a9ab5');g.addColorStop(1,'#1a5570')}
cx.fillStyle=g;cx.fill();
var ig=cx.createRadialGradient(x-12,y-15,4,x,y,38);ig.addColorStop(0,'rgba(255,255,255,.35)');ig.addColorStop(1,'rgba(255,255,255,0)');cx.fillStyle=ig;cx.fill();
var ey=y-4+Math.sin(tm)*2,es=is?3.5+Math.sin(tm*6)*1.2:3.5;cx.fillStyle='rgba(255,255,255,.9)';
cx.beginPath();cx.arc(x-13,ey,es,0,Math.PI*2);cx.fill();cx.beginPath();cx.arc(x+13,ey,es,0,Math.PI*2);cx.fill();
if(is){cx.beginPath();cx.ellipse(x,y+13,6,2.5+Math.sin(tm*8)*2.5,0,0,Math.PI*2);cx.fillStyle='rgba(255,255,255,.5)';cx.fill()}
else{cx.beginPath();cx.arc(x,y+15,7.5,.1*Math.PI,.9*Math.PI,0);cx.strokeStyle='rgba(255,255,255,.6)';cx.lineWidth=1.5;cx.stroke()}
for(var i=0;i<6;i++){var pa=i/6*Math.PI*2+tm*.5,pr=br+20+Math.sin(tm+i)*10;
cx.beginPath();cx.arc(x+Math.cos(pa)*pr,y+Math.sin(pa)*pr,1.2+Math.sin(tm*2+i)*.6,0,Math.PI*2);
cx.fillStyle=il?'rgba(99,220,255,.5)':is?'rgba(180,140,255,.5)':'rgba(120,200,220,.3)';cx.fill()}
requestAnimationFrame(aO)}aO();

// ── Camera ──
function tCam(){var b=document.getElementById('cb'),w=document.getElementById('cw'),v=document.getElementById('cv'),d=document.getElementById('lv'),vb=document.getElementById('vb');
if(ca){var s=v.srcObject;if(s)s.getTracks().forEach(function(t){t.stop()});v.srcObject=null;w.classList.remove('on');d.style.display='none';b.textContent='OFF';b.classList.remove('on');vb.classList.remove('show');ca=0}
else{navigator.mediaDevices.getUserMedia({video:1,audio:0}).then(function(s){v.srcObject=s;v.play();w.classList.add('on');d.style.display='flex';b.textContent='ON';b.classList.add('on');vb.classList.add('show');ca=1}).catch(function(){sS('Camera denied')})}}

// ── Speech ──
function tListen(){if(il){if(rc)rc.stop();il=0;uM();return}
var S=window.SpeechRecognition||window.webkitSpeechRecognition;if(!S){sS('No speech support');return}
rc=new S();rc.lang='ko-KR';rc.continuous=0;rc.interimResults=0;
rc.onstart=function(){il=1;sS('Listening...');document.getElementById('hnt').textContent='Speak now...';uM()};
rc.onresult=function(e){var t=e.results[0][0].transcript;il=0;uM();sM(t)};
rc.onerror=function(){il=0;sS('Try again');uM()};rc.onend=function(){il=0;uM()};rc.start()}
function uM(){document.getElementById('mic').classList.toggle('on',!!il);if(!il)document.getElementById('hnt').textContent='Tap orb to talk'}
function sp(t){if(!window.speechSynthesis)return;speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(t);u.lang='ko-KR';u.rate=1.05;u.pitch=1.15;u.onstart=function(){is=1};u.onend=function(){is=0};u.onerror=function(){is=0};speechSynthesis.speak(u)}

// ── Chat ──
function tChat(){co=!co;document.getElementById('cha').classList.toggle('op',co);document.getElementById('ctg').textContent=co?'Hide':'Chat'}
function sS(t){var e=document.getElementById('stt');e.textContent=t;e.classList.toggle('th',!!it)}
function aM(r,c){var ms=document.getElementById('msgs'),qb=document.getElementById('qbs');if(qb)qb.parentElement.remove();
// Process links and maps in assistant messages
if(r==='assistant'){
  // Convert [MAP:place] to embedded map
  c=c.replace(/\[MAP:([^\]]+)\]/g,function(m,place){
    var encoded=encodeURIComponent(place);
    return '<div style="margin:8px 0;border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,.1)"><iframe src="https://maps.google.com/maps?q='+encoded+'&output=embed&z=15" style="width:100%;height:200px;border:none"></iframe><a href="https://maps.google.com/maps?q='+encoded+'" target="_blank" style="display:block;padding:6px 12px;background:rgba(60,160,80,.1);color:#60c080;font-size:11px;text-decoration:none">&#x1f4cd; Open in Google Maps</a></div>';
  });
  // Convert [text](url) to clickable links
  c=c.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,'<a href="$2" target="_blank" style="color:#60b0e0;text-decoration:underline">$1 &#x1f517;</a>');
  // Convert plain URLs to clickable
  c=c.replace(/(^|[^"'])(https?:\/\/[^\s<]+)/g,'$1<a href="$2" target="_blank" style="color:#60b0e0;text-decoration:underline">$2</a>');
}
var d=document.createElement('div');d.className='m '+(r==='user'?'u':'a');
d.innerHTML='<div class="b">'+(r==='assistant'?'<span class="ll">LUMI</span>':'')+c+'</div>';ms.appendChild(d);ms.scrollTop=ms.scrollHeight}
function shT(){var ms=document.getElementById('msgs'),d=document.createElement('div');d.className='m a';d.id='td';
d.innerHTML='<div class="b"><span class="ll">LUMI</span><div class="dt"><i></i><i></i><i></i></div></div>';ms.appendChild(d);ms.scrollTop=ms.scrollHeight}
function rmT(){var e=document.getElementById('td');if(e)e.remove()}
function sM(t){if(!t.trim())return;
// Check if it's an image generation request
var imgWords=['\uADF8\uB824','\uADF8\uB9BC','\uB9CC\uB4E4\uC5B4','\uC0DD\uC131','\uADF8\uB9AC','\uB514\uC790\uC778','draw','paint','generate','create image'];
var isImg=imgWords.some(function(w){return t.toLowerCase().includes(w)});
if(isImg){genImg(t);return}
aM('user',t);it=1;sS('Thinking...');shT();
fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify({message:t})})
.then(function(r){return r.json()}).then(function(d){rmT();it=0;sS('LUMI');aM('assistant',d.reply);sp(d.reply)})
.catch(function(){rmT();it=0;sS('LUMI');aM('assistant','Connection error...')})}

// ── Image Generation ──
function genImg(prompt){
aM('user',prompt);it=1;sS('Drawing...');shT();
fetch('/imagine',{method:'POST',headers:{'Content-Type':'application/json; charset=utf-8'},body:JSON.stringify({prompt:prompt})})
.then(function(r){return r.json()}).then(function(d){
  rmT();it=0;sS('LUMI');
  if(d.svg){
    var html='<span class="ll">LUMI</span>';
    html+='<div style="margin-bottom:6px">그려봤어! 🎨</div>';
    html+='<div style="background:linear-gradient(135deg,#1a2030,#0d1520);border-radius:14px;padding:12px;margin-top:6px;width:320px;height:320px;display:flex;align-items:center;justify-content:center;overflow:hidden">'+d.svg.replace('viewBox="0 0 600 600"','viewBox="0 0 600 600" width="300" height="300"')+'</div>';
    var ms=document.getElementById('msgs'),div=document.createElement('div');
    div.className='m a';div.innerHTML='<div class="b" style="padding:10px;max-width:95%">'+html+'</div>';
    ms.appendChild(div);ms.scrollTop=ms.scrollHeight;
    sp('그려봤어! 어때?');
  }else if(d.image_b64){
    var html='<span class="ll">LUMI</span>';
    html+='<div style="margin-bottom:6px">그려봤어! 🎨</div>';
    html+='<img src="data:image/jpeg;base64,'+d.image_b64+'" style="width:100%;border-radius:12px;margin-top:4px"/>';
    html+='<a download="lumi_art_'+Date.now()+'.jpg" href="data:image/jpeg;base64,'+d.image_b64+'" style="display:inline-block;margin-top:8px;padding:6px 14px;background:rgba(160,100,255,.15);border:1px solid rgba(160,100,255,.25);border-radius:10px;color:#b090e0;font-size:11px;text-decoration:none;cursor:pointer">&#x1f4be; Save Image</a>';
    var ms=document.getElementById('msgs'),div=document.createElement('div');
    div.className='m a';div.innerHTML='<div class="b" style="padding:10px;max-width:95%">'+html+'</div>';
    ms.appendChild(div);ms.scrollTop=ms.scrollHeight;
    sp('그려봤어! 어때?');
  }else{aM('assistant', d.error || '그리기 실패... 다시 해볼래? 😅')}
}).catch(function(){rmT();it=0;sS('LUMI');aM('assistant','Error...')})}

function sI(){var i=document.getElementById('ci'),t=i.value.trim();if(!t||it)return;i.value='';sM(t)}
function sQ(t){if(t.includes('\uBD10')){if(ca){snapAndSend()}else{sS('Turn on camera!');tCam()}}else{sM(t)}}
document.getElementById('ci').addEventListener('input',function(){document.getElementById('sbn').classList.toggle('on',this.value.trim().length>0)});
</script>
</body></html>"""

if __name__=="__main__":
    print("="*50)
    print("  LUMI - Home AI Companion")
    print("  (Groq + Vision + Weather + Memo)")
    print("="*50)
    print("  Open: http://localhost:5000")
    print("  Stop: Ctrl+C")
    print("="*50)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0",port=port,debug=False)