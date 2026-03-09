import os
import json
import time
import requests
import re
import telebot
from playwright.sync_api import sync_playwright

# CONFIGURACIÓN (Railway toma esto de tus Variables)
TOKEN = os.getenv("TELEGRAM_TOKEN", "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE")
CHAT_ID = os.getenv("CHAT_ID", "8191397359")
SMS_KEY = os.getenv("SMS_KEY", "4fff057f7ba6b313169973cde3a8d7bf")

bot = telebot.TeleBot(TOKEN)

def send_log(msg):
    print(msg)
    try:
        bot.send_message(CHAT_ID, f"📢 **Estado:** {msg}", parse_mode="Markdown")
    except:
        pass

# --- FUNCIÓN DE CORREO MEJORADA ---
def get_mail():
    # Lista de dominios disponibles en 1secmail
    domains = ["1secmail.com", "1secmail.org", "1secmail.net"]
    for dom in domains:
        try:
            res = requests.get(f"https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1").json()
            if res:
                return res[0]
        except:
            continue
    return None

def wait_for_otp(email):
    user, domain = email.split('@')
    send_log("📩 Esperando el código OTP de Amazon...")
    for _ in range(30): # 3 minutos de espera
        time.sleep(6)
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
        try:
            msgs = requests.get(url).json()
            for m in msgs:
                if "amazon" in m['from'].lower() or "verification" in m['subject'].lower():
                    # Leer el cuerpo del mensaje
                    msg_id = m['id']
                    read_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain={domain}&id={msg_id}"
                    full = requests.get(read_url).json()
                    otp = re.search(r'(\d{6})', full['body'])
                    if otp:
                        return otp.group(1)
        except:
            continue
    return None

# --- PROCESO PRINCIPAL ---
def run_bot():
    send_log("🚀 **Iniciando proceso de registro en Amazon**")
    
    with sync_playwright() as p:
        # Lanzamos el navegador
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        try:
            # 1. Correo
            email = get_mail()
            if not email:
                send_log("❌ Error fatal: No se pudo generar un correo temporal.")
                return
            send_log(f"📧 Correo asignado: `{email}`")

            # 2. Formulario de Amazon
            send_log("🔗 Navegando a Amazon Register...")
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle", timeout=60000)

            send_log("✍️ Llenando datos: Manuel Perez...")
            page.fill("#ap_customer_name", "Manuel Perez")
            page.fill("#ap_email", email)
            page.fill("#ap_password", "Admin.2026$")
            page.fill("#ap_password_check", "Admin.2026$")
            
            send_log("🔘 Click en 'Continuar'...")
            page.click("#continue")
            
            # 3. Esperar OTP
            otp = wait_for_otp(email)
            if otp:
                send_log(f"🔢 OTP Recibido: `{otp}`. Insertando...")
                # Esperar a que el campo de OTP esté visible
                page.wait_for_selector("input[name='code']", timeout=10000)
                page.fill("input[name='code']", otp)
                page.click("#cvf-submit-otp-button")
                page.wait_for_load_state("networkidle")
                send_log("✅ Código verificado.")
            else:
                send_log("❌ El código OTP nunca llegó. Abortando.")
                return

            # 4. Finalización y Cookies
            send_log("🍪 ¡Registro exitoso! Generando archivo de Cookies...")
            time.sleep(5)
            cookies = context.cookies()
            
            # Guardar Cookies en JSON
            cookie_file = "amazon_cookies.json"
            with open(cookie_file, "w") as f:
                json.dump(cookies, f, indent=2)
            
            # Enviar el archivo a Telegram
            with open(cookie_file, "rb") as doc:
                bot.send_document(CHAT_ID, doc, caption="📦 **Aquí tienes tus Cookies de Amazon**\nCuenta creada con éxito.")

        except Exception as e:
            send_log(f"⚠️ Error durante el proceso: {str(e)}")
            # Tomar foto del error para saber qué pasó
            page.screenshot(path="error.png")
            with open("error.png", "rb") as photo:
                bot.send_photo(CHAT_ID, photo, caption="📸 Captura del error en Amazon")
        finally:
            browser.close()
            send_log("🏁 Bot finalizado.")

if __name__ == "__main__":
    run_bot()
