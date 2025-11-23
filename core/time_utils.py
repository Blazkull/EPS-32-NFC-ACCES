from datetime import datetime, timedelta, timezone

def to_colombia_time(utc_time: datetime) -> datetime:
    """
    Convierte UTC a hora de Colombia (UTC-5)
    """
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=timezone.utc)
    
    colombia_tz = timezone(timedelta(hours=-5))
    return utc_time.astimezone(colombia_tz)

def format_colombia_time(utc_time: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Convierte UTC a hora Colombia y formatea como string
    """
    colombia_time = to_colombia_time(utc_time)
    return colombia_time.strftime(format_str)

def get_current_colombia_time() -> datetime:
    """
    Obtiene la hora actual en Colombia
    """
    return to_colombia_time(datetime.utcnow())

def format_colombia_time_for_display(utc_time: datetime) -> str:
    """
    Formato más legible para interfaz de usuario
    """
    return format_colombia_time(utc_time, "%d/%m/%Y %I:%M:%S %p")