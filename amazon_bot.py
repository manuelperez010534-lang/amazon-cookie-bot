import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
import time
from playwright.async_api import async_playwright

# === CONFIGURACIÓN ===
TOKEN = "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE"
CHAT_ID = "8191397359"
AC_KEY = "37f2bc34098021f0fcb8ed61cc7b3782"

# Tu Proxy Premium
PROXY_ADDR = "31.59.20.176:6754"
PROXY_USER = "hyqgyxhf"
PROXY_PASS = "30z9ho40bxvp"

PROXY_CONFIG = {
    "server": f"http://{PROXY_ADDR}",
    "username": PROXY_USER,
    "password": PROXY_PASS
}

REQUESTS_PROXIES = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_ADDR}/"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 {msg}", parse_mode="Markdown")
    except: pass

# --- MANEJO DE CORREO (MAIL.TM API) ---
class MailTM:
    def __init__(self):
        self.api = "https://api.mail.tm"
        self.session = requests.Session()
        self.session.proxies = REQUESTS_PROXIES
        self.address = ""
        self.password = "ZeusBot2026!"
        self.token = ""

    def get_account(self):
        try:
            domain = self.session.get(f"{self.api}/domains").json()['hydra:member'][0]['domain']
            self.address = f"zeus{random.randint(1000,9999)}@{domain}"
            res = self.session.post(f"{self.api}/accounts", json={
                "address": self.address, "password": self.password
            }, timeout=30)
            
            auth = self.session.post(f"{self.api}/token", json={
                "address": self.address, "password": self.password
            }).json()
            self.token = auth['token']
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            return self.address
        except Exception as e:
            send_log(f"❌ Error Mail.tm: {e}")
            return None

    async def wait_for_otp(self):
        send_log("📩 Esperando OTP en Mail.tm...")
        for _ in range(20):
            await asyncio.sleep(8)
            try:
                msgs = self.session.get(f"{self.api}/messages").json()['hydra:member']
                if msgs:
                    msg_id = msgs[0]['id']
                    content = self.session.get(f"{self.api}/messages/{msg_id}").json()['text']
                    otp = re.search(r'(\d{6})', content)
                    if otp: return otp.group(1)
            except: continue
        return None

# --- RESOLUTOR DE CAPTCHA ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img: return False
        
        img_url = await captcha_img.get_attribute("src")
        img_res = requests.get(img_url, proxies=REQUESTS_PROXIES, timeout=30)
        img_b64 = base64.b64encode(img_res.content).decode('utf-8')

        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY, "task": {"type": "ImageToTextTask", "body": img_b64}
        }).json()
        
        task_id = task.get("taskId")
        for _ in range(15):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }).json()
            if res.get("status") == "ready":
                text = res["solution"]["text"]
                send_log(f"✅ Captcha: `{text}`")
                await page.fill("#captchacharacters", text)
                await page.press("#captchacharacters", "Enter")
                return True
    except: pass
    return False

# --- FLUJO DE REGISTRO ---
async def create_amazon():
    mail_service = MailTM()
    email = mail_service.get_account()
    if not email: return

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0")
            page = await context.new_page()

            send_log(f"🚀 Creando: `{email}`")
            await page.goto("https://www.amazon.com/ap/register", timeout=60000)
            await solve_captcha(page)

            await page.fill("#ap_customer_name", f"Zeus {random.randint(10,99)}")
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "Admin.2026.!")
            await page.fill("#ap_password_check", "Admin.2026.!")
            await page.click("#continue")
            
            await asyncio.sleep(5)
            await solve_captcha(page)

            otp = await mail_service.wait_for_otp()
            if otp:
                send_log(f"🔢 OTP: `{otp}`")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(10000)
                
                cookies = await context.cookies()
                with open("session.json", "w") as f: json.dump(cookies, f)
                with open("session.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Amazon Creada: {email}")
            else:
                send_log("❌ OTP no recibido.")
        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
        finally:
            await browser.close()

# --- BOT INTERFACE ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "ZeuS Bot Online. Usa /crear para una cuenta Amazon.")

@bot.message_handler(commands=['crear'])
def run_cmd(message):
    bot.reply_to(message, "⚙️ Iniciando proceso...")
    asyncio.run(create_amazon())

if __name__ == "__main__":
    send_log("🔥 Bot iniciado correctamente en Railway")
    bot.infinity_polling()
