import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
from playwright.async_api import async_playwright

# === CONFIG ===
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
    try: bot.send_message(CHAT_ID, f"🤖 **Amazon:** {msg}", parse_mode="Markdown")
    except: pass

# --- RESOLUTOR DIRECTO POR API (SIN LIBRERÍAS) ---
async def solve_captcha_direct(page):
    captcha_img = await page.query_selector('img[src*="captcha"]')
    if not captcha_img: return False

    try:
        send_log("🧩 Captcha detectado. Resolviendo...")
        img_url = await captcha_img.get_attribute("src")
        img_content = requests.get(img_url).content
        img_b64 = base64.b64encode(img_content).decode('utf-8')

        # Crear Tarea
        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_b64}
        }).json()
        
        task_id = task.get("taskId")
        if not task_id: return False

        # Consultar Resultado
        for _ in range(20):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }).json()
            if res.get("status") == "ready":
                code = res["solution"]["text"]
                send_log(f"✅ Resuelto: `{code}`")
                await page.fill("#captchacharacters", code)
                await page.press("#captchacharacters", "Enter")
                return True
    except Exception as e: print(f"Error captcha: {e}")
    return False

# --- CORREO TEMPORAL ---
class Mailer:
    def __init__(self):
        self.sess = requests.Session()
        self.url = "https://www.guerrillamail.com/ajax.php"
    
    async def get_email(self):
        r = self.sess.get(f"{self.url}?f=get_email_address").json()
        return r['email_addr']

    async def get_otp(self):
        send_log("📩 Esperando OTP...")
        for _ in range(12):
            await asyncio.sleep(10)
            r = self.sess.get(f"{self.url}?f=check_email&seq=0").json()
            for m in r.get('list', []):
                if "amazon" in m['mail_from'].lower():
                    full = self.sess.get(f"{self.url}?f=fetch_email&email_id={m['mail_id']}").json()
                    otp = re.search(r'(\d{6})', full['mail_body'])
                    if otp: return otp.group(1)
        return None

# --- MOTOR PRINCIPAL ---
async def main():
    mailer = Mailer()
    user_name = f"Zeus_{random.randint(100,999)}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        try:
            email = await mailer.get_email()
            send_log(f"🚀 Iniciando: `{email}`")

            await page.goto("https://www.amazon.com/ap/register")
            await solve_captcha_direct(page)

            await page.fill("#ap_customer_name", user_name)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "ZeuS_2026_!")
            await page.fill("#ap_password_check", "ZeuS_2026_!")
            await page.click("#continue")
            
            await asyncio.sleep(4)
            await solve_captcha_direct(page)

            otp = await mailer.get_otp()
            if otp:
                send_log(f"🔢 OTP: `{otp}`")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_load_state("networkidle")
                
                # Guardar Sesión
                cookies = await context.cookies()
                with open("sesion.json", "w") as f: json.dump(cookies, f)
                with open("sesion.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Creada: {email}")
            else:
                send_log("❌ No llegó el OTP")

        except Exception as e: send_log(f"⚠️ Error: {str(e)}")
        finally: await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
