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

# --- RESOLUTOR DIRECTO API CON VALIDACIÓN ---
async def solve_captcha(page):
    try:
        captcha_img = await page.query_selector('img[src*="captcha"]')
        if not captcha_img: return False

        send_log("🧩 Captcha detectado, resolviendo...")
        img_url = await captcha_img.get_attribute("src")
        response = requests.get(img_url, timeout=10)
        img_data = base64.b64encode(response.content).decode('utf-8')

        # Crear tarea
        task_res = requests.post("https://api.anti-captcha.com/createTask", json={
            "clientKey": AC_KEY,
            "task": {"type": "ImageToTextTask", "body": img_data}
        }, timeout=10)
        
        task = task_res.json()
        task_id = task.get("taskId")
        if not task_id: 
            send_log(f"❌ Error Anti-Captcha: {task.get('errorDescription')}")
            return False

        # Pull del resultado
        for _ in range(20):
            await asyncio.sleep(3)
            res_poll = requests.post("https://api.anti-captcha.com/getTaskResult", json={
                "clientKey": AC_KEY, "taskId": task_id
            }, timeout=10).json()
            
            if res_poll.get("status") == "ready":
                captcha_text = res_poll["solution"]["text"]
                send_log(f"✅ Texto: {captcha_text}")
                await page.fill("#captchacharacters", captcha_text)
                await page.press("#captchacharacters", "Enter")
                return True
    except Exception as e:
        send_log(f"⚠️ Error en Captcha: {str(e)}")
    return False

# --- CORREO TEMPORAL CON PROTECCIÓN ---
class Mailer:
    def __init__(self):
        self.session = requests.Session()
        self.url = "https://www.guerrillamail.com/ajax.php"

    async def get_mail(self):
        try:
            r = self.session.get(f"{self.url}?f=get_email_address", timeout=10)
            return r.json()['email_addr']
        except Exception as e:
            send_log("❌ Guerrilla Mail bloqueó la IP del Proxy.")
            raise e

    async def get_otp(self):
        send_log("📩 Esperando el código OTP...")
        for _ in range(15):
            await asyncio.sleep(10)
            try:
                r = self.session.get(f"{self.url}?f=check_email&seq=0", timeout=10).json()
                for m in r.get('list', []):
                    if "amazon" in m['mail_from'].lower():
                        full = self.session.get(f"{self.url}?f=fetch_email&email_id={m['mail_id']}", timeout=10).json()
                        otp = re.search(r'(\d{6})', full['mail_body'])
                        if otp: return otp.group(1)
            except: continue
        return None

# --- FLUJO ---
async def start():
    mailer = Mailer()
    nombre = f"User{random.randint(1000, 9999)}"
    
    async with async_playwright() as p:
        # Usamos chromium con ignore_https_errors para evitar bloqueos por proxy
        browser = await p.chromium.launch(headless=True, proxy=PROXY)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0",
            ignore_https_errors=True
        )
        page = await context.new_page()

        try:
            email = await mailer.get_mail()
            send_log(f"🚀 Intentando cuenta: {email}")

            # Ir a Amazon con tiempo de espera largo
            await page.goto("https://www.amazon.com/ap/register", wait_until="networkidle", timeout=60000)
            
            await solve_captcha(page)

            await page.fill("#ap_customer_name", nombre)
            await page.fill("#ap_email", email)
            await page.fill("#ap_password", "ZeusPass2026!")
            await page.fill("#ap_password_check", "ZeusPass2026!")
            
            # Click y esperar navegación
            await asyncio.gather(
                page.click("#continue"),
                page.wait_for_load_state("networkidle")
            )
            
            await asyncio.sleep(5)
            await solve_captcha(page)

            otp = await mailer.get_otp()
            if otp:
                send_log(f"🔢 OTP Recibido: {otp}")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_timeout(5000)
                
                cookies = await context.cookies()
                with open("sesion.json", "w") as f: json.dump(cookies, f)
                with open("sesion.json", "rb") as f:
                    bot.send_document(CHAT_ID, f, caption=f"✅ ÉXITO: {email}")
            else:
                send_log("❌ Tiempo de espera de OTP agotado.")

        except Exception as e:
            send_log(f"💥 Error Crítico: {str(e)}")
            # Tomar captura del error para ver qué pasó
            await page.screenshot(path="debug.png")
            with open("debug.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="Captura del momento del error")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(start())
