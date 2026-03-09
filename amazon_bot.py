import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
from playwright.async_api import async_playwright

# === CONFIGURACIÓN ===
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
AC_KEY = os.getenv("ANTI_CAPTCHA_KEY", "37f2bc34098021f0fcb8ed61cc7b3782")

# Proxy Webshare
PROXY = {
    "server": "http://p.webshare.io:80",
    "username": "vgdgihxr-rotate",
    "password": "czeted9ynghb"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"📢 **Bot Amazon:** {msg}", parse_mode="Markdown")
    except: pass

# --- FUNCIÓN PROPIA PARA ANTI-CAPTCHA (SIN LIBRERÍAS) ---
async def solve_amazon_captcha(page):
    captcha_img = await page.query_selector('img[src*="captcha"]')
    if not captcha_img: return False

    try:
        send_log("🧩 Captcha detectado. Resolviendo vía API...")
        img_url = await captcha_img.get_attribute("src")
        
        # Descargar imagen y convertir a Base64
        img_data = base64.b64encode(requests.get(img_url).content).decode('utf-8')
        
        # Crear tarea en Anti-Captcha
        create_task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_data}
        }).json()
        
        task_id = create_task.get("taskId")
        if not task_id: return False

        # Esperar resultado
        for _ in range(10):
            await asyncio.sleep(3)
            result = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }).json()
            if result.get("status") == "ready":
                captcha_text = result["solution"]["text"]
                send_log(f"✅ Captcha resuelto: `{captcha_text}`")
                await page.fill("#captchacharacters", captcha_text)
                await page.press("#captchacharacters", "Enter")
                return True
    except: pass
    return False

# --- MANEJO DE CORREO (Guerrilla Mail) ---
class MailBox:
    def __init__(self):
        self.session = requests.Session()
        self.email = ""
    
    async def get_mail(self):
        res = self.session.get("https://www.guerrillamail.com/ajax.php?f=get_email_address").json()
        self.email = res['email_addr']
        return self.email

    async def wait_otp(self):
        send_log("📩 Esperando código de Amazon...")
        for _ in range(15):
            await asyncio.sleep(10)
            res = self.session.get("https://www.guerrillamail.com/ajax.php?f=check_email&seq=0").json()
            for m in res.get('list', []):
                if "amazon" in m['mail_from'].lower():
                    full = self.session.get(f"https://www.guerrillamail.com/ajax.php?f=fetch_email&email_id={m['mail_id']}").json()
                    otp = re.search(r'(\d{6})', full['mail_body'])
                    if otp: return otp.group(1)
        return None

# --- PROCESO DE REGISTRO ---
async def run_bot():
    mailbox = MailBox()
    name = f"User_{random.randint(1000, 9999)}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        try:
            email = await mailbox.get_mail()
            send_log(f"🚀 Creando cuenta: `{name}`\n📧 Correo: `{email}`")

            await page.goto("https://www.amazon.com/ap/register")
            await solve_amazon_captcha(page)

            await page.fill("#ap_customer_name", name)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "Admin.2026$")
            await page.fill("#ap_password_check", "Admin.2026$")
            await page.click("#continue")
            
            await asyncio.sleep(5)
            await solve_amazon_captcha(page)

            otp = await mailbox.wait_otp()
            if otp:
                send_log(f"🔢 OTP Recibido: `{otp}`")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_load_state("networkidle")
                
                # Éxito: Cookies
                cookies = await context.cookies()
                with open("cookies.json", "w") as f: json.dump(cookies, f, indent=2)
                with open("cookies.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta Creada: {email}")
            else:
                send_log("❌ No se recibió OTP.")

        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
