import requests
import json
import time
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta
from flask import Flask
import threading

# Initialize Yemen Local Timezone (UTC+3)
YEMEN_TZ = timezone(timedelta(hours=3))

LOG_FILE = os.path.join(os.path.dirname(__file__), "bot_runtime.log")

def write_log(text):
    t_str = datetime.now(YEMEN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{t_str}] {text}"
    print(msg, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ================= Configuration =================
GEMINI_KEY = "AQ.Ab8RN6KdRtAIgXs2jf--Ice6_M0Ek3FI52wP8_ImRvuTsCoPlg"
GEMINI_KEY_BACKUP = "AQ.Ab8RN6LWRUAfe0UVLpJREfXxfg_qr5TE0A7Mj0lQ2jlPFiDLhQ"

TRELLO_KEY = "c07e6b1745c5b2785d9369af2f0cc8e1"
TRELLO_TOKEN = "ATTAf0d15d61fe7a7e240338c0cf4873147044f4c9447bc1b73e2d1c67aa537ad8b2514481A5"
TRELLO_BOARD_ID = "6ae02725b7d6cc6e5e00836f"
TRELLO_AUTH = {"key": TRELLO_KEY, "token": TRELLO_TOKEN}
CONTROL_CARD_ID = "6ae177ac72bba1c9dd200369"
MEETING_CARD_ID = "6ae23c81b175ea9e269e2a98"
MEETING_URL = "https://meet.google.com/ypx-fgth-rie"

GMAIL_SENDER = "r.dalselwi@gmail.com"
GMAIL_APP_PASSWORD = "zvhs jrde dqtz bjgq"

CHECK_INTERVAL_SECONDS = 5
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), "processed_events.json")

TEAM_DIRECTORY = {
    "amgedanees": {
        "name": "أمجد أنيس الحوباني",
        "tag": "@amgedanees",
        "email": "amgedanees650@gmail.com"
    },
    "refai3": {
        "name": "الفاتح عبد الكريم الرفاعي",
        "tag": "@refai3",
        "email": "refai7408@gmail.com"
    },
    "esmailalziadi": {
        "name": "إسماعيل محمد مرشد الزيادي",
        "tag": "@esmailalziadi",
        "email": "esmailalziyaidi@gmail.com"
    },
    "ahmed_shawqi": {
        "name": "أحمد شوقي",
        "tag": "@ahmed_shawqi",
        "email": "ahmedshwqyhh@gmail.com"
    },
    "raadfahdalselwi": {
        "name": "رعد فهد عبده الصلوي",
        "tag": "@raadfahdalselwi",
        "email": "r.dalselwi@gmail.com"
    }
}

ALL_TEAM_TAGS = " ".join([m["tag"] for m in TEAM_DIRECTORY.values()])
ALL_TEAM_EMAILS = [m["email"] for m in TEAM_DIRECTORY.values()]

CHAPTER_MAPPING = {
    "الفصل الأول": {
        "card_name": "📖 الفصل الأول: المقدمة ومنهجية العمل (Introduction & Methodology)",
        "assigned_tags": ["@raadfahdalselwi", "@refai3", "@amgedanees", "@esmailalziadi", "@ahmed_shawqi"],
        "emails": ALL_TEAM_EMAILS
    },
    "الفصل الثاني": {
        "card_name": "📊 الفصل الثاني: الدراسات السابقة والجدوى والمخاطر (Literature Review & Feasibility)",
        "assigned_tags": ["@raadfahdalselwi", "@refai3", "@amgedanees", "@esmailalziadi", "@ahmed_shawqi"],
        "emails": ALL_TEAM_EMAILS
    },
    "الفصل الثالث": {
        "card_name": "📝 الفصل الثالث: تحليل النظام والمتطلبات وقصص المستخدمين (Analysis & Requirements)",
        "assigned_tags": ["@amgedanees", "@ahmed_shawqi"],
        "emails": ["amgedanees650@gmail.com", "ahmedshwqyhh@gmail.com", "r.dalselwi@gmail.com"]
    },
    "الفصل الرابع": {
        "card_name": "📐 الفصل الرابع: تصميم النظام والـ ERD والمعمارية وقواعد البيانات (System Design)",
        "assigned_tags": ["@amgedanees", "@ahmed_shawqi"],
        "emails": ["amgedanees650@gmail.com", "ahmedshwqyhh@gmail.com", "r.dalselwi@gmail.com"]
    },
    "الفصل الخامس": {
        "card_name": "💻 الفصل الخامس: التنفيذ البرمجي وبناء المنصة (Implementation & Coding)",
        "assigned_tags": ["@raadfahdalselwi", "@esmailalziadi"],
        "emails": ["r.dalselwi@gmail.com", "esmailalziyaidi@gmail.com"]
    },
    "الفصل السادس": {
        "card_name": "🧪 الفصل السادس: الاختبار وتكامل النظام والنتائج والتوصيات (Testing & Deployment)",
        "assigned_tags": ["@raadfahdalselwi", "@esmailalziadi"],
        "emails": ["r.dalselwi@gmail.com", "esmailalziyaidi@gmail.com"]
    }
}

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"actions": [], "control_checks": []}
    return {"actions": [], "control_checks": []}

def save_processed(data):
    try:
        with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        write_log(f"Error saving processed: {e}")

def send_real_email(recipients, subject, body_text):
    try:
        msg = MIMEText(body_text, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = f"GPMP Platform <{GMAIL_SENDER}>"
        msg["To"] = ", ".join(recipients)
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, recipients, msg.as_string())
        server.quit()
        write_log(f"📧 [Email Sent]: تم إرسال الإيميل بنجاح إلى: {recipients}")
        return True
    except Exception as e:
        write_log(f"❌ [Email Error]: {e}")
        return False

def ask_gemini_smart_reply(member_info, text_content, card_name, has_file=False, file_name="", is_meeting=False):
    user_name = member_info["name"]
    user_tag = member_info["tag"]
    
    if is_meeting:
        prompt = (
            f"أنت مستشار الذكاء الاصطناعي لمشروع GPMP بجامعة الرازي.\n"
            f"قام مدير المشروع {user_name} بنشر إشعار اجتماع: {text_content}.\n"
            f"اكتب تنبيهاً رسمياً موجزاً ومشجعاً للحضور في الموعد (سطرين إلى 3 أسطر فقط)."
        )
    else:
        file_desc = f"قام العضو برفع ملف توثيق رسمي مرفق باسم ({file_name})" if has_file else "العضو لم يرفع ملف Word أو PDF حتى الآن"
        prompt = (
            f"أنت مستشار الذكاء الاصطناعي الأكاديمي لمشروع GPMP بجامعة الرازي - قسم IT بإشراف د. يحيى الأشموري.\n"
            f"المطلوب: رد ذكي ومشجع وموجز (2-3 أسطر) موجه للزميل:\n"
            f"- الاسم: {user_name} ({user_tag})\n"
            f"- البطاقة: {card_name}\n"
            f"- المحتوى: {text_content}\n"
            f"- حالة المرفق: {file_desc}\n\n"
            f"القواعد: ابدأ بالمنشن واسم الزميل، إذا رفع ملف أثنِ على رفع الملف ({file_name})، وإذا لم يرفع ملف نبهه بلطف بضرورة إرفاق ملف Word/PDF. لا تضع أي توقيعات إضافية."
        )

    for k in [GEMINI_KEY, GEMINI_KEY_BACKUP]:
        for m in ["gemini-3.1-flash-lite", "gemini-3.1-flash-preview"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"
            try:
                r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=8)
                if r.status_code == 200:
                    cand = r.json().get("candidates", [])
                    if cand and "parts" in cand[0].get("content", {}):
                        return cand[0]["content"]["parts"][0]["text"].strip()
            except Exception:
                continue
    return None

def check_card_has_member_file(card_id, username):
    try:
        atts = requests.get(f"https://api.trello.com/1/cards/{card_id}/attachments", params=TRELLO_AUTH, timeout=10).json()
        for a in atts:
            aname = a.get("name", "").lower()
            member_ar = TEAM_DIRECTORY.get(username, {}).get("name", "").split()[0]
            if any(ext in aname for ext in [".docx", ".doc", ".pdf"]):
                if member_ar in aname or username in aname:
                    return True, a.get("name")
        if atts:
            return True, atts[-1].get("name")
    except Exception:
        pass
    return False, ""

def get_cards_map():
    try:
        cards = requests.get(f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/cards", params=TRELLO_AUTH, timeout=10).json()
        return {c.get("name"): c.get("id") for c in cards}
    except Exception:
        return {}

def check_control_card_triggers():
    processed = load_processed()
    processed_checks = set(processed.get("control_checks", []))
    newly_processed = False
    
    try:
        cls = requests.get(f"https://api.trello.com/1/cards/{CONTROL_CARD_ID}/checklists", params=TRELLO_AUTH, timeout=10).json()
    except Exception:
        return
        
    cards_map = None
    for cl in cls:
        for item in cl.get("checkItems", []):
            item_id = item["id"]
            state = item["state"]
            item_name = item["name"]
            
            if state == "incomplete" and item_id in processed_checks:
                processed_checks.discard(item_id)
                newly_processed = True

            if state == "complete" and item_id not in processed_checks:
                write_log(f"⚡ تفعيل إشعار جديد من مركز التحكم: {item_name}")
                
                matched_chapter = None
                for ch_key in CHAPTER_MAPPING:
                    if ch_key in item_name:
                        matched_chapter = ch_key
                        break
                        
                if matched_chapter:
                    if cards_map is None:
                        cards_map = get_cards_map()
                    info = CHAPTER_MAPPING[matched_chapter]
                    target_card_name = info["card_name"]
                    target_card_id = cards_map.get(target_card_name)
                    mentions = " ".join(info["assigned_tags"])
                    recipients = info["emails"]
                    
                    email_subject = f"🚨 تكليف رسمي: تفعيل العمل على {matched_chapter} - منصة GPMP"
                    email_body = (
                        f"السلام عليكم ورحمة الله وبركاته، زملاءنا الأعزاء في مشروع التخرج GPMP 🎓\n\n"
                        f"إشعار وتكليف رسمي من مدير المشروع (رعد فهد الصلوي):\n"
                        f"تم اعتماد وتفعيل العمل رسمياً على [{matched_chapter}].\n\n"
                        f"المطلوب من كل عضو معني:\n"
                        f"1. البدء الفوري بإنجاز المهام المحددة للفصل.\n"
                        f"2. رفع مسودة التوثيق بصيغة (Word أو PDF) داخل بطاقة تريلو وصفحة Notion.\n\n"
                        f"رابط لوحة العمل على Trello:\nhttps://trello.com/b/OOGtmMQq\n\n"
                        f"بالتوفيق للجميع! 🚀"
                    )
                    send_real_email(recipients, email_subject, email_body)
                    
                    if target_card_id:
                        trello_text = (
                            f"🚨 **[إشعار وتكليف رسمي من مدير المشروع: رعد الصلوي]**\n\n"
                            f"إلى الزملاء الأعزاء: {mentions}\n\n"
                            f"📌 **المهمة:** تم اعتماد وتفعيل العمل رسمياً على **{matched_chapter}**.\n"
                            f"يرجى البدء الفوري برفع مسودات التوثيق بصيغة (Word / PDF) هنا لاعتمادها.\n\n"
                            f"📧 تم إرسال إشعار بريدي مباشر إلى: `{', '.join(recipients)}`"
                        )
                        requests.post(f"https://api.trello.com/1/cards/{target_card_id}/actions/comments", params={**TRELLO_AUTH, "text": trello_text})
                    
                    processed_checks.add(item_id)
                    newly_processed = True
                    write_log(f"✅ تم تنفيذ وإرسال إشعار {matched_chapter} بنجاح عبر الإيميل وتريلو!")
                    try:
                        requests.put(f"https://api.trello.com/1/cards/{CONTROL_CARD_ID}/checkItem/{item_id}", params={**TRELLO_AUTH, "state": "incomplete"}, timeout=10)
                    except Exception as err:
                        write_log(f"Error resetting checkItem: {err}")

                elif any(k in item_name for k in ["اجتماع", "تذكير", "إشعار عام"]):
                    recipients = ALL_TEAM_EMAILS
                    
                    email_subject = f"📢 تنبيه عاجل من مدير المشروع: {item_name} - مشروع GPMP"
                    email_body = (
                        f"السلام عليكم ورحمة الله وبركاته، كافة أعضاء فريق GPMP 🎓\n\n"
                        f"تنبيه وتوجيه هام من مدير المشروع (رعد الصلوي):\n"
                        f"{item_name}\n\n"
                        f"🔗 رابط الاجتماع المرئي المباشر:\n{MEETING_URL}\n\n"
                        f"يرجى الحضور والالتزام في الموعد المحدد.\n"
                        f"رابط لوحة Trello: https://trello.com/b/OOGtmMQq"
                    )
                    send_real_email(recipients, email_subject, email_body)
                    
                    trello_meet_text = (
                        f"📢 **[تنبيه هام وعاجل من مدير المشروع: رعد الصلوي]**\n\n"
                        f"إلى كافة أعضاء الفريق: {ALL_TEAM_TAGS}\n\n"
                        f"📌 **الموضوع:** {item_name}\n\n"
                        f"🔗 **رابط الاجتماع المباشر:** {MEETING_URL}\n\n"
                        f"📧 تم إرسال رسالة بريد إلكتروني رسمية إلى كافة الأعضاء:\n`{', '.join(ALL_TEAM_EMAILS)}`"
                    )
                    requests.post(f"https://api.trello.com/1/cards/{CONTROL_CARD_ID}/actions/comments", params={**TRELLO_AUTH, "text": trello_meet_text})
                    
                    processed_checks.add(item_id)
                    newly_processed = True
                    write_log(f"✅ تم إرسال تنبيه الاجتماع بنجاح عبر الإيميل وتريلو!")
                    try:
                        requests.put(f"https://api.trello.com/1/cards/{CONTROL_CARD_ID}/checkItem/{item_id}", params={**TRELLO_AUTH, "state": "incomplete"}, timeout=10)
                    except Exception as err:
                        write_log(f"Error resetting checkItem: {err}")

    if newly_processed:
        processed["control_checks"] = list(processed_checks)
        save_processed(processed)

def process_cycle():
    processed = load_processed()
    processed_actions = set(processed.get("actions", []))
    
    check_control_card_triggers()

    actions_url = f"https://api.trello.com/1/boards/{TRELLO_BOARD_ID}/actions"
    try:
        actions = requests.get(actions_url, params={**TRELLO_AUTH, "filter": "commentCard,addAttachmentToCard", "limit": 15}, timeout=10).json()
    except Exception as e:
        write_log(f"Error fetching board actions: {e}")
        return

    newly_handled = False
    for act in reversed(actions):
        act_id = act.get("id")
        if act_id in processed_actions:
            continue
            
        act_type = act.get("type")
        card_data = act.get("data", {}).get("card", {})
        card_id = card_data.get("id")
        card_name = card_data.get("name", "")
        creator = act.get("memberCreator", {})
        username = creator.get("username", "")
        
        member_info = TEAM_DIRECTORY.get(username, {
            "name": creator.get("fullName", "عضو الفريق"),
            "tag": f"@{username}",
            "email": ""
        })
        
        act_date = act.get("date", "")
        time_str = ""
        if act_date:
            try:
                dt = datetime.fromisoformat(act_date.replace("Z", "+00:00")).astimezone(YEMEN_TZ)
                time_str = dt.strftime("%I:%M %p")
            except Exception:
                pass

        if act_type == "commentCard":
            raw_text = act.get("data", {}).get("text", "")
            
            if any(k in raw_text for k in ["🤖", "مستشار الذكاء الاصطناعي", "🚨 [إشعار وتكليف", "📢 [تنبيه هام", "📝 [محضر اجتماع"]):
                processed_actions.add(act_id)
                newly_handled = True
                continue

            # Feature: Meeting Summary Broadcast to Email and Trello
            if any(kw in raw_text for kw in ["ملخص الاجتماع", "محضر الاجتماع", "قرارات الاجتماع", "نقاط الاجتماع"]):
                write_log(f"📝 اكتشاف ملخص اجتماع جديد من {member_info['name']}...")
                now_str = datetime.now(YEMEN_TZ).strftime('%Y-%m-%d | %I:%M %p')
                email_sub = f"📝 [محضر اجتماع رسمي] توثيق اجتماع مشروع GPMP ({now_str})"
                email_content = (
                    f"السلام عليكم ورحمة الله وبركاته، كافة أعضاء فريق GPMP 🎓\n\n"
                    f"قام مدير المشروع ({member_info['name']}) بنشر وتوثيق محضر الاجتماع الرسمي:\n\n"
                    f"📅 التاريخ والوقت: {now_str} (توقيت صنعاء)\n"
                    f"🔗 منصة الاجتماع: {MEETING_URL}\n\n"
                    f"📌 تفاصيل ومحضر الاجتماع:\n"
                    f"{raw_text}\n\n"
                    f"رابط لوحة Trello: https://trello.com/b/OOGtmMQq\n\n"
                    f"بالتوفيق للجميع! 🚀\n"
                    f"مدير المشروع: رعد الصلوي"
                )
                send_real_email(ALL_TEAM_EMAILS, email_sub, email_content)
                
                trello_meeting_post = (
                    f"📝 **[تم اعتماد وإرسال محضر الاجتماع للبريد الإلكتروني بنجاح]**\n\n"
                    f"إلى كافة أعضاء الفريق: {ALL_TEAM_TAGS}\n\n"
                    f"⏰ **التوقيت:** `{now_str}`\n"
                    f"📧 تم إرسال نص المحضر أعلاه تلقائياً إلى بريد جميع أعضاء الفريق الخمسة بنجاح."
                )
                requests.post(f"https://api.trello.com/1/cards/{card_id}/actions/comments", params={**TRELLO_AUTH, "text": trello_meeting_post})
                processed_actions.add(act_id)
                newly_handled = True
                write_log("✅ تم إرسال محضر الاجتماع بنجاح إلى الإيميل وتريلو!")
                continue

            is_meeting = False
            if username == "raadfahdalselwi" and any(k in raw_text for k in ["اجتماع", "meet.google.com"]):
                is_meeting = True
                
            has_file, file_name = check_card_has_member_file(card_id, username)
            write_log(f"معالجة تعليق فوري من {member_info['name']}...")
            ai_reply = ask_gemini_smart_reply(member_info, raw_text, card_name, has_file=has_file, file_name=file_name, is_meeting=is_meeting)
            
            if ai_reply:
                header = f"🤖 **[مستشار الذكاء الاصطناعي GPMP]**"
                if time_str:
                    header += f" *(وقت التسليم: {time_str})*"
                final_post = f"{header}\n\n{ai_reply}"
                
                post_url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
                post_res = requests.post(post_url, params={**TRELLO_AUTH, "text": final_post}, timeout=10)
                if post_res.status_code == 200:
                    bot_id = post_res.json().get("id")
                    processed_actions.add(act_id)
                    if bot_id:
                        processed_actions.add(bot_id)
                    newly_handled = True
                    write_log(f"✅ تم الرد الفوري بنجاح على {member_info['name']}")
            else:
                processed_actions.add(act_id)
                newly_handled = True

        elif act_type == "addAttachmentToCard":
            att_info = act.get("data", {}).get("attachment", {})
            file_name = att_info.get("name", "ملف توثيق")
            
            write_log(f"اكتشاف رفع ملف جديد ({file_name}) من {member_info['name']}...")
            ai_reply = ask_gemini_smart_reply(member_info, f"تم رفع ملف المشروع بصيغة رسمية: {file_name}", card_name, has_file=True, file_name=file_name)
            
            if ai_reply:
                header = f"🤖 **[مستشار الذكاء الاصطناعي GPMP]**"
                if time_str:
                    header += f" *(تم الرفع: {time_str})*"
                final_post = f"{header}\n\n{ai_reply}"
                
                post_url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
                post_res = requests.post(post_url, params={**TRELLO_AUTH, "text": final_post}, timeout=10)
                if post_res.status_code == 200:
                    bot_id = post_res.json().get("id")
                    processed_actions.add(act_id)
                    if bot_id:
                        processed_actions.add(bot_id)
                    newly_handled = True
                    write_log(f"✅ تم الرد الفوري على تسليم الملف من {member_info['name']}")
            else:
                processed_actions.add(act_id)
                newly_handled = True

    if newly_handled:
        processed["actions"] = list(processed_actions)
        save_processed(processed)

def bot_loop():
    write_log("=" * 70)
    write_log(" 🚀 بدء تشغيل نظام الأتمتة الشامل: Gmail SMTP + Trello + Gemini AI (24/7)")
    write_log(f" 📧 خادم البريد المعتمد: {GMAIL_SENDER} (متصل ومفعل)")
    write_log(f" 🔗 رابط الاجتماع المعتمد: {MEETING_URL}")
    write_log(" 🛑 تم تفعيل الاستجابة الفائقة وتوقيت اليمن UTC+3 ومحاضر الاجتماعات")
    write_log("=" * 70)
    
    while True:
        try:
            process_cycle()
        except Exception as e:
            write_log(f"تنبيه استثنائي: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)

# Flask app for Render Web Service health-check
app = Flask(__name__)

@app.route("/")
def index():
    return "GPMP Automation Bot is running 24/7 in the cloud! 🚀"

@app.route("/health")
def health():
    return {"status": "healthy", "service": "gpmp_bot"}

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

