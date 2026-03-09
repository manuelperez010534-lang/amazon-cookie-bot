import os
import json
import time
import requests
import re
import telebot
import subprocess
from playwright.sync_api import sync_playwright

# === CONFIGURACIÓN ===
# Railway toma estos valores de la pestaña "Variables"
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
SMS_KEY = os.getenv("SMS_KEY", "4fff057f7ba6b313169973cde3a8d7bf")

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"🤖 **Bot Amazon:** {msg}", parse_mode="Markdown")
    except Exception as e:
        print(f"Error enviando Telegram: {e}")

# --- UTILIDADES DE REGISTRO ---
def get_mail():
    try:
        res = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1").json()
        email = res[0]
        user, domain = email.split('@')
        return email, user, domain
    except:
        return None, None, None

def wait_for_otp_mail(user, domain):
    send_log("📩 Esperando código en el correo...")
    for _ in range(25):
        time.sleep(5)
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
        try:
            msgs = requests.get(url).json()
            for m in msgs:
                if "amazon" in m['from'].lower():
                    msg_id = m['id']
                    content = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain={domain}&id={msg_id}").json()
                    otp = re.search(r'(\d{6})', content['body'])
                    if otp: return otp.group(1)
        except:
            continue
    return None

# --- FLUJO PRINCIPAL ---
def run_bot():
    send_log("🚀 **Iniciando navegador...**")
    
    with sync_playwright() as p:
        try:
            # Configuración para servidores (Headless)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage"
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0"
            )
            page = context.new_page()

            # 1. Datos de registro
            email, user, domain = get_mail()
            if not email:
                send_log("❌ Error generando correo.")
                return

            send_log(f"📧 Correo generado: `{email}`")

            # 2. Navegación a Amazon
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")
            
            page.fill("#ap_customer_name", "Alex Hunter")
            page.fill("#ap_email", email)
            page.fill("#ap_password", "CookieBot2026!")
            page.fill("#ap_password_check", "CookieBot2026!")
            
            page.click("#continue")
            time.sleep(5)

            # 3. Manejo de OTP Correo
            otp = wait_for_otp_mail(user, domain)
            if otp:
                send_log(f"✅ OTP recibido: `{otp}`")
                if page.query_selector("input[name='code']"):
                    page.fill("input[name='code']", otp)
                    page.click("#cvf-submit-otp-button")
                    page.wait_for_load_state("networkidle")
            else:
                send_log("❌ Tiempo de espera de OTP agotado.")
                page.screenshot(path="timeout.png")
                with open("timeout.png", "rb") as f:
                    bot.send_photo(CHAT_ID, f, caption="Pantalla de Amazon al fallar")
                return

            # 4. Extracción de Cookies
            time.sleep(5)
            cookies = context.cookies()
            with open("cookies.json", "w") as f:
                json.dump(cookies, f, indent=2)
            
            send_log("🍪 **Cookies extraídas.** Enviando archivo...")
            with open("cookies.json", "rb") as f:
                bot.send_document(CHAT_ID, f, caption="✅ Registro Amazon Exitoso")

        except Exception as e:
            send_log(f"⚠ **Error en el proceso:** {str(e)}")
        finally:
            browser.close()
            send_log("🏁 Bot finalizado.")

if __name__ == "__main__":
    run_bot()
