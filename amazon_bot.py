import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
from playwright.async_api import async_playwright

# === DATOS ===
TOKEN = "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE"
CHAT_ID = "8191397359"
AC_KEY = "37f2bc34098021f0fcb8ed61cc7b3782"

PROXY = {
    "server": "http://p.webshare.io:80",
    "username": "vgdgihxr-rotate",
    "password": "czeted9ynghb"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 **Amazon Bot:** {msg}")
    except: pass

# --- RESOLUTOR DIRECTO API ---
async def solve_captcha(page):
    captcha_img = await page.query_selector('img[src*="captcha"]')
    if not captcha_img: return False

    try:
        send_log("🧩 Captcha detectado, resolviendo...")
        img_url = await captcha_img.get_attribute("src")
        img_data = base64.b64encode(requests.get(img_url).content).decode('utf-8')

        # Crear tarea
        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_data}
        }).json()
        
        task_id = task.get("taskId")
        if not task_id: return False

        # Pull del resultado
        for _ in range(20):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }).json()
            if res.get("status") == "ready":
                captcha_text = res["solution"]["text"]
                send_log(f"✅ Texto: {captcha_text}")
                await page.fill("#captchacharacters", captcha_text)
                await page.press("#captchacharacters", "Enter")
                return True
    except: pass
    return False

# --- CORREO TEMPORAL ---
class Mailer:
    def __init__(self):
        self.session = requests.Session()
        self.url = "https://www.guerrillamail.com/ajax.php"

    async def get_mail(self):
        r = self.session.get(f"{self.url}?f=get_email_address").json()
        return r['email_addr']

    async def get_otp(self):
        send_log("📩 Esperando el código OTP...")
        for _ in range(10):
            await asyncio.sleep(10)
            r = self.session.get(f"{self.url}?f=check_email&seq=0").json()
            for m in r.get('list', []):
                if "amazon" in m['mail_from'].lower():
                    full = self.session.get(f"{self.url}?f=fetch_email&email_id={m['mail_id']}").json()
                    otp = re.search(r'(\d{6})', full['mail_body'])
                    if otp: return otp.group(1)
        return None

# --- FLUJO ---
async def start():
    mailer = Mailer()
    nombre = f"TestUser{random.randint(100, 999)}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        try:
            email = await mailer.get_mail()
            send_log(f"🚀 Creando cuenta: {email}")

            await page.goto("https://www.amazon.com/ap/register")
            await solve_captcha(page)

            await page.fill("#ap_customer_name", nombre)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "Pass.2026.!")
            await page.fill("#ap_password_check", "Pass.2026.!")
            await page.click("#continue")
            
            await asyncio.sleep(5)
            await solve_captcha(page)

            otp = await mailer.get_otp()
            if otp:
                send_log(f"🔢 OTP Recibido: {otp}")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_load_state("networkidle")
                
                # Guardar Cookies
                cookies = await context.cookies()
                with open("amazon_cookies.json", "w") as f: json.dump(cookies, f)
                with open("amazon_cookies.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta OK: {email}")
            else:
                send_log("❌ No llegó el correo de Amazon.")

        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(start())
