import os
import json
import time
import requests
import re
import telebot
from playwright.sync_api import sync_playwright

# === CONFIGURACIÓN DE APIS (Usa Variables de Entorno en Railway) ===
TELEGRAM_TOKEN = "8461610558:AAG9_DipzDcqmWYmAbb-LucReBzsI4-t_bE"
CHAT_ID = "TU_CHAT_ID_AQUÍ"  # <--- CAMBIA ESTO (Usa @userinfobot en Telegram para saber el tuyo)
SMS_KEY = "4fff057f7ba6b313169973cde3a8d7bf"

# Inicializar Bot de Telegram
tbot = telebot.TeleBot(TELEGRAM_TOKEN)

def send_log(msg):
    print(msg)
    try:
        tbot.send_message(CHAT_ID, f"🤖 **Log:** {msg}", parse_mode="Markdown")
    except: pass

# --- FUNCIONES DE CORREO (1secmail) ---
def get_mail():
    res = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1").json()
    email = res[0]
    user, domain = email.split('@')
    return email, user, domain

def wait_for_otp_mail(user, domain):
    send_log("📩 Esperando OTP en el correo...")
    for _ in range(20):
        time.sleep(7)
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
        msgs = requests.get(url).json()
        for m in msgs:
            if "amazon" in m['from'].lower() or "verification" in m['subject'].lower():
                msg_id = m['id']
                content = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain={domain}&id={msg_id}").json()
                otp = re.search(r'(\d{6})', content['body'])
                if otp: return otp.group(1)
    return None

# --- FUNCIONES DE SMS (SMS-Activate) ---
def get_sms_number():
    # 'am' = Amazon, country=0 = Rusia (barato)
    url = f"https://api.sms-activate.org/stora/api/res.php?api_key={SMS_KEY}&action=getNumber&service=am&country=0"
    res = requests.get(url).text
    if "ACCESS_NUMBER" in res:
        parts = res.split(':')
        return parts[1], parts[2] # ID, Numero
    return None, None

def wait_for_otp_sms(id_op):
    send_log("📱 Esperando OTP de SMS...")
    url = f"https://api.sms-activate.org/stora/api/res.php?api_key={SMS_KEY}&action=getStatus&id={id_op}"
    for _ in range(30):
        time.sleep(10)
        res = requests.get(url).text
        if "STATUS_OK" in res:
            return res.split(':')[1]
    return None

# --- FLUJO PRINCIPAL ---
def run_bot():
    send_log("🚀 **Iniciando Proceso de Registro**")
    
    with sync_playwright() as p:
        # Configuración para Railway/Cloud
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0")
        page = context.new_page()

        try:
            # 1. Preparar Datos
            email, user, domain = get_mail()
            send_log(f"📧 Email: `{email}`")

            # 2. Navegar a Amazon
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")
            page.fill("#ap_customer_name", "Test User")
            page.fill("#ap_email", email)
            page.fill("#ap_password", "Pass.2026!$")
            page.fill("#ap_password_check", "Pass.2026!$")
            page.click("#continue")
            
            # 3. OTP Correo
            otp_m = wait_for_otp_mail(user, domain)
            if otp_m:
                send_log(f"✅ OTP Mail recibido: `{otp_m}`")
                page.fill("input[name='code']", otp_m)
                page.click("#cvf-submit-otp-button")
                page.wait_for_load_state("networkidle")
            else:
                send_log("❌ Error: OTP de correo no llegó.")
                return

            # 4. Verificar si pide SMS
            if "phone" in page.content().lower() or page.query_selector("#ap_phone_number"):
                sms_id, phone_num = get_sms_number()
                if phone_num:
                    send_log(f"📞 Usando número: `{phone_num}`")
                    # (Aquí iría la lógica de rellenar el input del teléfono si aparece)
                    # otp_s = wait_for_otp_sms(sms_id)
                else:
                    send_log("⚠️ No hay números disponibles en SMS-Activate.")

            # 5. Finalizar y enviar Cookies
            send_log("🍪 Extrayendo cookies finales...")
            cookies = context.cookies()
            cookies_json = json.dumps(cookies, indent=2)
            
            # Guardar y enviar archivo a Telegram
            with open("cookies.json", "w") as f:
                f.write(cookies_json)
            
            with open("cookies.json", "rb") as doc:
                tbot.send_document(CHAT_ID, doc, caption="✅ **¡Registro Exitoso!**\nAquí tienes las cookies.")

        except Exception as e:
            send_log(f"❌ **Error Crítico:** {str(e)}")
        finally:
            browser.close()
            send_log("🏁 Navegador cerrado.")

if __name__ == "__main__":
    run_bot()
