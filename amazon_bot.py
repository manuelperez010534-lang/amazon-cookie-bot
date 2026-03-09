import json
import time
import requests
import re
from playwright.sync_api import sync_playwright

# === CONFIGURACIÓN ===
SMS_ACTIVATE_KEY = "4fff057f7ba6b313169973cde3a8d7bf"
# Usamos 1secmail (Gratis, sin API Key)
API_MAIL_GEN = "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1"

def obtener_mail():
    res = requests.get(API_MAIL_GEN).json()
    email = res[0]
    user, domain = email.split('@')
    return email, user, domain

def buscar_otp_mail(user, domain):
    print(f"🔎 Buscando OTP en {user}@{domain}...")
    for _ in range(15):  # Reintenta durante 90 segundos
        time.sleep(6)
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={user}&domain={domain}"
        msgs = requests.get(url).json()
        for m in msgs:
            # Amazon suele enviar desde 'account-update@amazon.com' o similar
            if "amazon" in m['from'].lower() or "verification" in m['subject'].lower():
                id_msg = m['id']
                content = requests.get(f"https://www.1secmail.com/api/v1/?action=readMessage&login={user}&domain={domain}&id={id_msg}").json()
                # Busca 6 dígitos
                codigo = re.search(r'(\d{6})', content['body'])
                if codigo:
                    return codigo.group(1)
    return None

def obtener_numero_sms():
    # 'am' es el código de Amazon en SMS-Activate
    # country=0 es para Rusia (barato), puedes cambiar a 6 para España o 12 para USA
    url = f"https://api.sms-activate.org/stora/api/res.php?api_key={SMS_ACTIVATE_KEY}&action=getNumber&service=am&country=0"
    res = requests.get(url).text
    if "ACCESS_NUMBER" in res:
        # Formato: ACCESS_NUMBER:ID:NUMERO
        _, id_operacion, numero = res.split(':')
        return id_operacion, numero
    print(f"❌ Error SMS-Activate: {res}")
    return None, None

def buscar_otp_sms(id_op):
    print(f"📱 Esperando SMS de Amazon...")
    for _ in range(20):
        time.sleep(10)
        url = f"https://api.sms-activate.org/stora/api/res.php?api_key={SMS_ACTIVATE_KEY}&action=getStatus&id={id_op}"
        res = requests.get(url).text
        if "STATUS_OK" in res:
            return res.split(':')[1]
    return None

def ejecutar():
    with sync_playwright() as p:
        # Configuración para Render (Headless)
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = context.new_page()

        try:
            # 1. Datos iniciales
            email, user, domain = obtener_mail()
            print(f"📧 Usando: {email}")

            # 2. Navegar a Registro
            page.goto("https://www.amazon.com/ap/register", wait_until="networkidle")
            page.fill("#ap_customer_name", "Bot Testing")
            page.fill("#ap_email", email)
            page.fill("#ap_password", "AccounTest2026!")
            page.fill("#ap_password_check", "AccounTest2026!")
            page.click("#continue")

            # 3. OTP Correo
            otp_mail = buscar_otp_mail(user, domain)
            if otp_mail:
                print(f"✅ OTP Correo: {otp_mail}")
                # El selector del input puede variar según la región de Amazon
                page.fill("input[name='code']", otp_mail)
                page.click("#cvf-submit-otp-button")
                page.wait_for_load_state("networkidle")
            else:
                print("❌ No llegó el correo.")
                return

            # 4. SMS (Si Amazon lo solicita)
            # Nota: Si Amazon detecta el bot aquí pedirá Captcha. 
            # Si no, pedirá número de teléfono:
            if "phone" in page.content().lower() or page.query_selector("#ap_phone_number"):
                id_op, num = obtener_numero_sms()
                if num:
                    print(f"📞 Número obtenido: {num}")
                    page.fill("#ap_phone_number", num)
                    page.click("#continue") # O el botón correspondiente
                    
                    otp_sms = buscar_otp_sms(id_op)
                    if otp_sms:
                        print(f"✅ OTP SMS: {otp_sms}")
                        page.fill("input[name='code']", otp_sms)
                        page.click("#cvf-submit-otp-button")

            # 5. RESULTADO FINAL: COOKIES
            print("\n" + "="*40)
            print("🔑 EXTRACCIÓN DE COOKIES EXITOSA")
            cookies = context.cookies()
            print(json.dumps(cookies, indent=2))
            print("="*40 + "\n")

        except Exception as e:
            print(f"⚠️ Error en el flujo: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    ejecutar()
