import os
import json
import time
import requests
import re
import telebot
import random
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"📢 **Estado:** {msg}", parse_mode="Markdown")
    except: pass

# --- GENERADOR DE DATOS ALEATORIOS ---
def get_random_name():
    nombres = ["Manuel", "Jose", "Luis", "Carlos", "Andres", "Javier", "Pedro"]
    apellidos = ["Perez", "Garcia", "Rodriguez", "Sanchez", "Ramirez", "Torres"]
    return f"{random.choice(nombres)} {random.choice(apellidos)}"

# --- NUEVA FUNCIÓN DE CORREO (USANDO GUERRILLA MAIL API) ---
class MailBox:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.guerrillamail.com/ajax.php"
        self.email = ""
        self.sid_token = ""

    def get_email(self):
        res = self.session.get(f"{self.base_url}?f=get_email_address").json()
        self.email = res['email_addr']
        self.sid_token = res['sid_token']
        return self.email

    def check_otp(self):
        res = self.session.get(f"{self.base_url}?f=check_email&seq=0").json()
        for msg in res.get('list', []):
            if "amazon" in msg['mail_from'].lower():
                full_msg = self.session.get(f"{self.base_url}?f=fetch_email&email_id={msg['mail_id']}").json()
                otp = re.search(r'(\d{6})', full_msg['mail_body'])
                if otp: return otp.group(1)
        return None

# --- PROCESO PRINCIPAL ---
def run_bot():
    send_log("🚀 **Iniciando proceso con nombres aleatorios...**")
    mailbox = MailBox()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        try:
            # 1. Correo
            email = mailbox.get_email()
            if not email:
                send_log("❌ Error fatal: Guerrilla Mail no responde.")
                return
            
            nombre_completo = get_random_name()
            send_log(f"📧 Correo: `{email}`\n👤 Nombre: `{nombre_completo}`")

            # 2. Amazon
            send_log("🔗 Entrando a Amazon...")
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")

            send_log(f"✍️ Escribiendo datos de {nombre_completo}...")
            page.fill("#ap_customer_name", nombre_completo)
            page.fill("#ap_email", email)
            page.fill("#ap_password", "Admin.2026$")
            page.fill("#ap_password_check", "Admin.2026$")
            
            page.click("#continue")
            
            # 3. Esperar OTP (60 segundos máximo)
            send_log("📩 Esperando OTP en bandeja de entrada...")
            otp = None
            for _ in range(15):
                time.sleep(5)
                otp = mailbox.check_otp()
                if otp: break
            
            if otp:
                send_log(f"🔢 OTP Recibido: `{otp}`. Verificando...")
                page.fill("input[name='code']", otp)
                page.click("#cvf-submit-otp-button")
                page.wait_for_load_state("networkidle")
            else:
                send_log("❌ OTP no llegó. Puede que Amazon pida Captcha.")
                page.screenshot(path="failed.png")
                with open("failed.png", "rb") as f: bot.send_photo(CHAT_ID, f)
                return

            # 4. Finalizar y Cookies
            send_log("🍪 ¡Éxito! Extrayendo cookies...")
            time.sleep(5)
            cookies = context.cookies()
            
            with open("amazon_cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            
            with open("amazon_cookies.json", "rb") as doc:
                bot.send_document(CHAT_ID, doc, caption=f"✅ Cuenta creada para {nombre_completo}")

        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
        finally:
            browser.close()
            send_log("🏁 Bot finalizado.")

if __name__ == "__main__":
    run_bot()
