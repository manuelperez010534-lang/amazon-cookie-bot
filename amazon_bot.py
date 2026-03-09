import os
import json
import asyncio
import random
import re
import telebot
import requests
import base64
from playwright.async_api import async_playwright

# === DATOS DE CONFIGURACIÓN ===
TOKEN = "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE"
CHAT_ID = "8191397359"
AC_KEY = "37f2bc34098021f0fcb8ed61cc7b3782"

# Configuración del nuevo Proxy
PROXY_URL = "http://31.59.20.176:6754"
PROXY_AUTH = {
    "username": "hyqgyxhf",
    "password": "30z9ho40bxvp"
}

# Diccionario para requests
REQUESTS_PROXIES = {
    "http": f"http://{PROXY_AUTH['username']}:{PROXY_AUTH['password']}@31.59.20.176:6754/",
    "https": f"http://{PROXY_AUTH['username']}:{PROXY_AUTH['password']}@31.59.20.176:6754/"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 **Amazon Bot:** {msg}")
    except: pass

# --- RESOLUTOR DE CAPTCHA POR API ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img: return False

        send_log("🧩 Captcha detectado, enviando a Anti-Captcha...")
        img_url = await captcha_img.get_attribute("src")
        
        # Descargar usando el proxy
        response = requests.get(img_url, proxies=REQUESTS_PROXIES, timeout=15)
        img_data = base64.b64encode(response.content).decode('utf-8')

        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_data}
        }, timeout=15).json()
        
        task_id = task.get("taskId")
        if not task_id: return False

        for _ in range(20):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }, timeout=15).json()
            if res.get("status") == "ready":
                text = res["solution"]["text"]
                send_log(f"✅ Captcha resuelto: {text}")
                await page.fill("#captchacharacters", text)
                await page.press("#captchacharacters", "Enter")
                return True
    except Exception as e:
        send_log(f"⚠️ Error en captcha: {e}")
    return False

# --- CORREO TEMPORAL ---
class Mailer:
    def __init__(self):
        self.session = requests.Session()
        self.session.proxies = REQUESTS_PROXIES
        self.url = "https://www.guerrillamail.com/ajax.php"

    async def get_email(self):
        r = self.session.get(f"{self.url}?f=get_email_address", timeout=15)
        return r.json()['email_addr']

    async def get_otp(self):
        send_log("📩 Monitoreando bandeja de entrada...")
        for _ in range(15):
            await asyncio.sleep(10)
            try:
                r = self.session.get(f"{self.url}?f=check_email&seq=0", timeout=15).json()
                for m in r.get('list', []):
                    if "amazon" in m['mail_from'].lower():
                        full = self.session.get(f"{self.url}?f=fetch_email&email_id={m['mail_id']}", timeout=15).json()
                        otp = re.search(r'(\d{6})', full['mail_body'])
                        if otp: return otp.group(1)
            except: continue
        return None

# --- FLUJO DE REGISTRO ---
async def start():
    mailer = Mailer()
    nombre = f"User_{random.randint(100, 999)}"
    
    async with async_playwright() as p:
        # Configuración del navegador con el nuevo proxy
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": PROXY_URL,
                "username": PROXY_AUTH["username"],
                "password": PROXY_AUTH["password"]
            }
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0"
        )
        page = await context.new_page()

        try:
            email = await mailer.get_email()
            send_log(f"🚀 Iniciando registro con: {email}")

            await page.goto("https://www.amazon.com/ap/register", wait_until="networkidle", timeout=60000)
            await solve_captcha(page)

            await page.fill("#ap_customer_name", nombre)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "ZeusBot.2026!")
            await page.fill("#ap_password_check", "ZeusBot.2026!")
            
            await page.click("#continue")
            await page.wait_for_timeout(5000)
            
            # Verificación de segundo captcha o puzzles
            await solve_captcha(page)

            otp = await mailer.get_otp()
            if otp:
                send_log(f"🔢 OTP Recibido: {otp}")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(8000)
                
                cookies = await context.cookies()
                with open("sesion.json", "w") as f: json.dump(cookies, f)
                with open("sesion.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Amazon Creada: {email}")
            else:
                send_log("❌ El OTP no llegó a tiempo.")

        except Exception as e:
            send_log(f"💥 Error: {str(e)}")
            await page.screenshot(path="error.png")
            with open("error.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="Evidencia del error")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(start())
