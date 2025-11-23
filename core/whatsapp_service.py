import requests
from core.config import settings
from core.time_utils import get_current_colombia_time, format_colombia_time_for_display

class WhatsAppService:
    def __init__(self):
        self.api_key = settings.CALLMEBOT_API_KEY
        self.admin_phone = settings.ADMIN_PHONE_NUMBER

    async def send_notification(self, message: str):
        """Envía notificación por WhatsApp usando CallMeBot API"""
        if not self.api_key or not self.admin_phone:
            print("⚠️ Configuración de WhatsApp no disponible")
            return False

        try:
            url = f"https://api.callmebot.com/whatsapp.php"
            params = {
                'phone': self.admin_phone,
                'text': message,
                'apikey': self.api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                print("✅ Notificación WhatsApp enviada")
                return True
            else:
                print(f"❌ Error enviando WhatsApp: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error en servicio WhatsApp: {e}")
            return False

    async def send_access_notification(self, user_name: str, access_type: str, door: str = None):
        """Envía notificación de acceso"""
        timestamp = format_colombia_time_for_display(get_current_colombia_time())
        message = f"🚪 *Sistema de Acceso NFC*\n\n"
        message += f"👤 *Usuario:* {user_name}\n"
        message += f"🔑 *Tipo de acceso:* {access_type}\n"
        if door:
            message += f"🚪 *Puerta:* {door}\n"
        message += f"🕐 *Fecha/Hora:* {timestamp}\n"
        message += f"📍 *Sistema activo*"
        
        return await self.send_notification(message)

    async def send_emergency_notification(self, action: str, user_name: str):
        """Envía notificación de emergencia"""
        timestamp = format_colombia_time_for_display(get_current_colombia_time())
        message = f"🚨 *ALERTA DEL SISTEMA NFC*\n\n"
        message += f"⚠️ *Acción:* {action}\n"
        message += f"👤 *Usuario:* {user_name}\n"
        message += f"🕐 *Fecha/Hora:* {timestamp}\n"
        message += f"🔴 *Sistema en modo emergencia*"
        
        return await self.send_notification(message)

# Instancia global
whatsapp_service = WhatsAppService()