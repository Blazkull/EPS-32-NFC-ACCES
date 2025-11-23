from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from core.database import create_db_and_tables
from core.config import settings
from core.whatsapp_service import whatsapp_service
from core.time_utils import get_current_colombia_time, format_colombia_time_for_display

# Importar routers
from routers import (
    auth, users, devices, logs, actions, 
    health, ws_device, nfc_cards, access_pins
)

async def send_startup_notification():
    """Envía notificación de inicio del backend por WhatsApp"""
    try:
        timestamp = format_colombia_time_for_display(get_current_colombia_time())
        message = f"🚀 *BACKEND INICIADO EXITOSAMENTE*\n\n"
        message += f"📋 *Sistema:* {settings.PROJECT_NAME}\n"
        message += f"🕐 *Hora de inicio:* {timestamp}\n"
        message += f"🌐 *URL API:* http://localhost:8000\n"
        message += f"📚 *Docs API:* http://localhost:8000/docs\n"
        message += f"✅ *Estado:* Sistema operativo y listo\n\n"
        message += f"🔧 _Sistema de Acceso NFC Inteligente_"
        
        success = await whatsapp_service.send_notification(message)
        if success:
            print("✅ Notificación de inicio enviada por WhatsApp")
        else:
            print("⚠️ No se pudo enviar notificación de inicio por WhatsApp")
            
    except Exception as e:
        print(f"❌ Error enviando notificación de inicio: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando Sistema de Acceso NFC Inteligente...")
    print("📋 Creando tablas de base de datos...")
    create_db_and_tables()
    print("✅ Base de datos inicializada")
    
    # Enviar notificación de inicio (de forma asíncrona sin bloquear)
    asyncio.create_task(send_startup_notification())
    
    print("🌐 Servidor API listo en http://localhost:8000")
    print("📚 Documentación disponible en http://localhost:8000/docs")
    yield
    
    # Shutdown
    print("🔴 Apagando sistema...")
    
    # Opcional: Enviar notificación de apagado
    try:
        timestamp = format_colombia_time_for_display(get_current_colombia_time())
        shutdown_message = f"🔴 *BACKEND APAGADO*\n\n"
        shutdown_message += f"📋 *Sistema:* {settings.PROJECT_NAME}\n"
        shutdown_message += f"🕐 *Hora de apagado:* {timestamp}\n"
        shutdown_message += f"📉 *Estado:* Sistema fuera de línea\n\n"
        shutdown_message += f"🔧 _Sistema de Acceso NFC Inteligente_"
        
        await whatsapp_service.send_notification(shutdown_message)
        print("✅ Notificación de apagado enviada por WhatsApp")
    except Exception as e:
        print(f"❌ Error enviando notificación de apagado: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Sistema de Control de Acceso Inteligente con NFC y ESP32",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(devices.router)
app.include_router(logs.router)
app.include_router(actions.router)
app.include_router(health.router)
app.include_router(ws_device.router)
app.include_router(nfc_cards.router)
app.include_router(access_pins.router)

@app.get("/")
async def root():
    """Endpoint raíz - Información del sistema"""
    return {
        "message": "🚀 Sistema de Acceso NFC Inteligente",
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "health_check": "/health"
    }

@app.get("/test-whatsapp")
async def test_whatsapp():
    """
    Endpoint para probar manualmente las notificaciones de WhatsApp
    """
    try:
        timestamp = format_colombia_time_for_display(get_current_colombia_time())
        test_message = f"🧪 *PRUEBA DE NOTIFICACIÓN*\n\n"
        test_message += f"📋 *Sistema:* {settings.PROJECT_NAME}\n"
        test_message += f"🕐 *Hora de prueba:* {timestamp}\n"
        test_message += f"🔧 *Tipo:* Prueba manual desde API\n"
        test_message += f"✅ *Resultado esperado:* Notificación recibida\n\n"
        test_message += f"🔧 _Sistema de Acceso NFC Inteligente_"
        
        success = await whatsapp_service.send_notification(test_message)
        
        if success:
            return {
                "success": True,
                "message": "✅ Notificación de prueba enviada exitosamente por WhatsApp",
                "timestamp": timestamp
            }
        else:
            return {
                "success": False,
                "message": "❌ No se pudo enviar la notificación de prueba por WhatsApp",
                "timestamp": timestamp
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Error enviando notificación de prueba: {str(e)}",
            "timestamp": format_colombia_time_for_display(get_current_colombia_time())
        }

@app.get("/system-info")
async def system_info():
    """Información detallada del sistema"""
    import platform
    import psutil
    from datetime import datetime
    
    # Información del sistema
    system_info = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "system": platform.system(),
        "machine": platform.machine(),
    }
    
    # Uso de recursos
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    resources = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "memory_percent": memory.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_percent": disk.percent,
    }
    
    return {
        "system": system_info,
        "resources": resources,
        "startup_time": format_colombia_time_for_display(get_current_colombia_time()),
        "project_name": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )