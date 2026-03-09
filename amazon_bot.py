import os
import json
import asyncio
import random
import re
import telebot
import requests
from playwright.async_api import async_playwright
from anticaptchaofficial.imagecaptcha import imagecaptcha

# === CONFIGURACIÓN ===
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
# Tu clave de Anti-Captcha (Asegúrate de tener saldo)
AC_KEY = os.getenv("ANTI_CAPTCHA_KEY", "37f2bc34098021f0fcb8ed61cc7b3782")

# Configuración de Proxy (Webshare)
PROXY = {
    "server": "http://p.webshare.io:80",
    "username": "vgdgihxr-rotate",
    "password": "czeted9ynghb"
}

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"📢 **Estado:** {msg}", parse_mode="Markdown")
    except:
        pass

# --- GENERADOR DE IDENTIDAD ---
def get_random_identity():
    nombres = ["Marcos", "Adrian", "Ricardo", "Samuel", "Julian", "Lucas"]
    apellidos = ["Vargas", "Mendoza", "Castro", "Reyes", "Guzman", "Soto"]
    return f"{random.choice(nombres)} {random.choice(apellidos)}"

# --- MANEJO DE CORREO TEMPORAL ---
class MailBox:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.guerrillamail.com/ajax.php"
        self.email = ""
        self.sid = ""

    async def create_mail(self):
        res = self.session.get(f"{self.base_url}?f=get_email_address").json()
        self.email = res['email_addr']
        self.sid = res['sid_token']
        return self.email

    async def get_otp(self):
        send_log("📩 Esperando OTP en Guerrilla Mail...")
        for _ in range(20):
            await asyncio.sleep(8)
            res = self.session.get(f"{self.base_url}?f=check_email&seq=0").json()
            for m in res.get('list', []):
                if "amazon" in m['mail_from'].lower():
                    full = self.session.get(f"{self.base_url}?f=fetch_email&email_id={m['mail_id']}").json()
                    match = re.search(r'(\d{6})', full['mail_body'])
                    if match: return match.group(1)
        return None

# --- RESOLUTOR DE CAPTCHA ---
async def solve_captcha(page):
    captcha_img = await page.query_selector('img[src*="captcha"]')
    if captcha_img:
        send_log("🧩 Captcha detectado. Enviando a Anti-Captcha...")
        img_url = await captcha_img.get_attribute("src")
        
        solver = imagecaptcha()
        solver.set_api_key(AC_KEY)
        # Descarga la imagen y la resuelve
        captcha_text = solver.solve_and_return_solution(img_url)
        if captcha_text:
            send_log(f"✅ Captcha resuelto: `{captcha_text}`")
            await page.fill("#captchacharacters", captcha_text)
            await page.press("#captchacharacters", "Enter")
            await page.wait_for_timeout(3000)
            return True
    return False

# --- FLUJO PRINCIPAL ---
async def start_bot():
    mailbox = MailBox()
    identity = get_random_identity()
    
    async with async_playwright() as p:
        # Lanzar navegador con tu Proxy
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0",
            viewport={'width': 1280, 'height': 720}
        )
        
        page = await context.new_page()
        
        try:
            email = await mailbox.create_mail()
            send_log(f"🚀 Iniciando: `{identity}`\n📧 Email: `{email}`")

            await page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")

            # Paso 0: ¿Hay captcha inicial?
            await solve_captcha(page)

            # Paso 1: Llenar Registro
            send_log("✍️ Escribiendo datos...")
            await page.type("#ap_customer_name", identity, delay=100)
            await page.type("#ap_email", email, delay=100)
            await page.type("#ap_password", "ZeuS.Bot.2026", delay=100)
            await page.type("#ap_password_check", "ZeuS.Bot.2026", delay=100)
            
            await page.click("#continue")
            await page.wait_for_timeout(5000)

            # Paso 2: ¿Hay captcha después del click?
            await solve_captcha(page)

            # Paso 3: OTP
            otp = await mailbox.get_otp()
            if otp:
                send_log(f"🔢 OTP recibido: `{otp}`. Verificando...")
                await page.fill("input[name='code']", otp)
                await page.click("#cvf-submit-otp-button")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)
            else:
                send_log("❌ No se recibió el código OTP.")
                return

            # Paso 4: Cookies Finales
            send_log("🍪 Registro completado. Extrayendo sesión...")
            cookies = await context.cookies()
            
            cookie_path = "amazon_session.json"
            with open(cookie_path, "w") as f:
                json.dump(cookies, f, indent=4)
            
            with open(cookie_path, "rb") as f:
                bot.send_document(CHAT_ID, f, caption=f"✅ Cuenta Amazon Creada\n👤 {identity}\n📧 {email}")

        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
            await page.screenshot(path="error_snap.png")
            with open("error_snap.png", "rb") as f:
                bot.send_photo(CHAT_ID, f, caption="Captura del error")
        finally:
            await browser.close()
            send_log("🏁 Proceso terminado.")

if __name__ == "__main__":
    asyncio.run(start_bot())
