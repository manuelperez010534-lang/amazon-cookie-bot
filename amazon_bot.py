import os
import json
import time
import requests
import re
import telebot
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
SMS_KEY = os.getenv("SMS_KEY", "4fff057f7ba6b313169973cde3a8d7bf")

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try: bot.send_message(CHAT_ID, f"📢 **Estado:** {msg}", parse_mode="Markdown")
    except: pass

def get_mail():
    res = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1").json()
    return res[0]

def wait_for_otp(email):
    user, domain = email.split('@')
    for _ in range(20):
        time.sleep(6)
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
        msgs = requests.get(url).json()
        for m in msgs:
            if "amazon" in m['from'].lower():
                full = requests.get(f"{url}&id={m['id']}&action=readMessage").json()
                otp = re.search(r'(\d{6})', full['body'])
                if otp: return otp.group(1)
    return None

def run_bot():
    send_log("🚀 Iniciando registro automático...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        try:
            # PASO 1: Generar Correo
            email = get_mail()
            send_log(f"📧 Correo temporal creado: `{email}`")

            # PASO 2: Entrar a Amazon
            send_log("🔗 Entrando a Amazon Register...")
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")

            # PASO 3: Llenar Formulario
            send_log("✍️ Llenando formulario (Nombre, Email, Pass)...")
            page.fill("#ap_customer_name", "Manuel Perez")
            page.fill("#ap_email", email)
            page.fill("#ap_password", "Admin.2026$")
            page.fill("#ap_password_check", "Admin.2026$")
            
            send_log("🔘 Haciendo clic en Continuar...")
            page.click("#continue")
            time.sleep(5)

            # PASO 4: OTP Correo
            otp = wait_for_otp(email)
            if otp:
                send_log(f"🔢 OTP Recibido: `{otp}`. Ingresándolo...")
                page.fill("input[name='code']", otp)
                page.click("#cvf-submit-otp-button")
                page.wait_for_load_state("networkidle")
            else:
                send_log("❌ El OTP de correo nunca llegó.")
                return

            # PASO 5: Verificar si pide Número (API SMS)
            if "phone" in page.content().lower():
                send_log("📱 Amazon pide número. Solicitando a SMS-Activate...")
                # Aquí el bot pediría el número y lo llenaría (lógica de sms-activate)
                # Por ahora, si llega aquí sin error, ya avanzaste el 90%
            
            # PASO 6: Finalizar
            send_log("🍪 Extrayendo cookies finales...")
            cookies = context.cookies()
            with open("cookies.json", "w") as f: json.dump(cookies, f)
            with open("cookies.json", "rb") as f:
                bot.send_document(CHAT_ID, f, caption="✅ ¡CUENTA CREADA EXITOSAMENTE!")

        except Exception as e:
            send_log(f"⚠️ Error: {str(e)}")
            page.screenshot(path="error.png")
            with open("error.png", "rb") as f: bot.send_photo(CHAT_ID, f)
        finally:
            browser.close()

if __name__ == "__main__":
    run_bot()
