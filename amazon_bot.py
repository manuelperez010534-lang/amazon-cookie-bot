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

# === DATOS DE CONFIGURACIÓN ===
TOKEN = "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE"
CHAT_ID = "8191397359"
AC_KEY = "37f2bc34098021f0fcb8ed61cc7b3782"

# Configuración del Proxy (Premium con Auth)
PROXY_URL = "http://31.59.20.176:6754"
PROXY_USER = "hyqgyxhf"
PROXY_PASS = "30z9ho40bxvp"

REQUESTS_PROXIES = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@31.59.20.176:6754/",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@31.59.20.176:6754/"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"🤖 **Amazon Bot:** {msg}")
    except: pass

# --- MANEJO DE CORREO CON REINTENTOS (ANTI-TIMEOUT) ---
class Mailer:
    def __init__(self):
        self.session = requests.Session()
        self.session.proxies = REQUESTS_PROXIES
        self.url = "https://www.guerrillamail.com/ajax.php"

    def safe_get(self, params):
        """Reintenta 3 veces si el proxy da timeout"""
        for i in range(3):
            try:
                return self.session.get(self.url, params=params, timeout=35)
            except Exception as e:
                if i == 2: raise e
                time.sleep(3)
        return None

    async def get_email(self):
        r = self.safe_get({"f": "get_email_address"})
        return r.json()['email_addr']

    async def get_otp(self):
        send_log("📩 Monitoreando OTP (Timeout 35s)...")
        for _ in range(12): # 2 minutos de espera total
            await asyncio.sleep(10)
            try:
                r = self.safe_get({"f": "check_email", "seq": "0"}).json()
                for m in r.get('list', []):
                    if "amazon" in m['mail_from'].lower():
                        full = self.safe_get({"f": "fetch_email", "email_id": m['mail_id']}).json()
                        otp = re.search(r'(\d{6})', full['mail_body'])
                        if otp: return otp.group(1)
            except: continue
        return None

# --- RESOLUTOR DE CAPTCHA DIRECTO ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img: return False

        send_log("🧩 Captcha detectado...")
        img_url = await captcha_img.get_attribute("src")
        
        # Descargar imagen usando el proxy
        img_res = requests.get(img_url, proxies=REQUESTS_PROXIES, timeout=30)
        img_b64 = base64.b64encode(img_res.content).decode('utf-8')

        task = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_b64}
        }, timeout=30).json()
        
        task_id = task.get("taskId")
        if not task_id: return False

        for _ in range(15):
            await asyncio.sleep(3)
            res = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }, timeout=30).json()
            if res.get("status") == "ready":
                text = res["solution"]["text"]
                send_log(f"✅ Resuelto: {text}")
                await page.fill("#captchacharacters", text)
                await page.press("#captchacharacters", "Enter")
                return True
    except: pass
    return False

# --- PROCESO PRINCIPAL ---
async def run():
    mailer = Mailer()
    nombre = f"Zeus_{random.randint(1000, 9999)}"
    
    async with async_playwright() as p:
        # Navegador configurado con tu Proxy
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": PROXY_URL,
                "username": PROXY_USER,
                "password": PROXY_PASS
            }
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0"
        )
        page = await context.new_page()

        try:
            email = await mailer.get_email()
            send_log(f"🚀 Iniciando: {email}")

            await page.goto("https://www.amazon.com/ap/register", timeout=60000)
            await solve_captcha(page)

            # Formulario
            await page.fill("#ap_customer_name", nombre)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "Admin.2026.!")
            await page.fill("#ap_password_check", "Admin.2026.!")
            await page.click("#continue")
            
            await asyncio.sleep(5)
            await solve_captcha(page)

            # OTP
            otp = await mailer.get_otp()
            if otp:
                send_log(f"🔢 OTP Recibido: {otp}")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(10000)
                
                # Guardar Cookies Finales
                cookies = await context.cookies()
                with open("sesion_amazon.json", "w") as f: json.dump(cookies, f)
                with open("sesion_amazon.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta Creada: {email}")
            else:
                send_log("❌ El OTP nunca llegó.")

        except Exception as e:
            send_log(f"⚠️ Fallo: {str(e)}")
            await page.screenshot(path="fallo.png")
            with open("fallo.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="Evidencia del error")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
