import os
import json
import asyncio
import random
import re
import telebot
import requests
from playwright.async_api import async_playwright
from anticaptchaofficial.imagecaptcha import imagecaptcha

# === CONFIGURACIÓN GLOBAL ===
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
ANTI_CAPTCHA_KEY = os.getenv("ANTI_CAPTCHA_KEY", "37f2bc34098021f0fcb8ed61cc7b3782")

# Proxy Config (Siguiendo tu ejemplo)
PROXY_SERVER = "http://p.webshare.io:80"
PROXY_AUTH = {"username": "vgdgihxr-rotate", "password": "czeted9ynghb"}

bot = telebot.TeleBot(TOKEN)

def send_telegram(msg):
    try: bot.send_message(CHAT_ID, f"🤖 **Amazon Engine:** {msg}", parse_mode="Markdown")
    except: pass

# === UTILIDADES DE CORREO (GuerrillaMail Asíncrono) ===
class MailBox:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.guerrillamail.com/ajax.php"
        self.email = ""
        self.sid_token = ""

    async def get_email(self):
        res = self.session.get(f"{self.base_url}?f=get_email_address").json()
        self.email = res['email_addr']
        self.sid_token = res['sid_token']
        return self.email

    async def wait_for_otp(self):
        for _ in range(20):
            await asyncio.sleep(7)
            res = self.session.get(f"{self.base_url}?f=check_email&seq=0").json()
            for msg in res.get('list', []):
                if "amazon" in msg['mail_from'].lower():
                    full = self.session.get(f"{self.base_url}?f=fetch_email&email_id={msg['mail_id']}").json()
                    otp = re.search(r'(\d{6})', full['mail_body'])
                    if otp: return otp.group(1)
        return None

# === RESOLUTOR DE CAPTCHA ===
async def solve_amazon_captcha(page):
    captcha_img = await page.query_selector('img[src*="captcha"]')
    if captcha_img:
        send_telegram("🧩 CAPTCHA detectado. Resolviendo...")
        img_url = await captcha_img.get_attribute("src")
        
        solver = imagecaptcha()
        solver.set_api_key(ANTI_CAPTCHA_KEY)
        # Descargar imagen y resolver
        captcha_text = solver.solve_and_return_solution(img_url)
        if captcha_text:
            await page.fill("#captchacharacters", captcha_text)
            await page.press("#captchacharacters", "Enter")
            await page.wait_for_timeout(2000)
            return True
    return False

# === LÓGICA PRINCIPAL (PLAYWRIGHT ASYNC) ===
async def run_registration():
    mailbox = MailBox()
    email = await mailbox.get_email()
    name = f"User_{random.randint(100,999)}"
    
    async with async_playwright() as p:
        # Lanzar con Proxy
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY_SERVER, "username": PROXY_AUTH["username"], "password": PROXY_AUTH["password"]}
        )
        
        # Simulación de Navegador Real (Headers)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            send_telegram(f"🚀 Iniciando registro para: `{email}`")
            await page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")

            # Manejo de Captcha inicial si aparece
            await solve_amazon_captcha(page)

            # Llenar Formulario con delays humanos
            await page.type("#ap_customer_name", name, delay=random.randint(50, 150))
            await page.type("#ap_email", email, delay=random.randint(50, 150))
            await page.type("#ap_password", "ZeuS_2026_!", delay=random.randint(50, 150))
            await page.type("#ap_password_check", "ZeuS_2026_!", delay=random.randint(50, 150))
            
            await page.click("#continue")
            await page.wait_for_timeout(3000)

            # Verificar si pide OTP
            otp = await mailbox.wait_for_otp()
            if otp:
                send_telegram(f"✅ OTP obtenido: `{otp}`")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_load_state("networkidle")
            else:
                send_telegram("❌ No se recibió OTP a tiempo.")
                return

            # Extraer Cookies finales
            cookies = await context.cookies()
            with open("amazon_cookies.json", "w") as f:
                json.dump(cookies, f, indent=4)
            
            with open("amazon_cookies.json", "rb") as f:
                bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta Creada: {email}")

        except Exception as e:
            send_telegram(f"⚠️ Error Crítico: {str(e)}")
            await page.screenshot(path="debug.png")
            with open("debug.png", "rb") as f: bot.send_photo(CHAT_ID, f)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_registration())

