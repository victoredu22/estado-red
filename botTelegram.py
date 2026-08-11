import asyncio
import ctypes
import datetime
import os
import socket
import sys
from pathlib import Path

# Forzar salida en UTF-8 para evitar errores de codificación en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def get_system_uptime() -> str:
    try:
        lib = ctypes.windll.kernel32
        try:
            uptime_ms = lib.GetTickCount64()
        except AttributeError:
            uptime_ms = lib.GetTickCount()
        sec = int(uptime_ms / 1000)
        days, sec = divmod(sec, 86400)
        hours, sec = divmod(sec, 3600)
        minutes, seconds = divmod(sec, 60)

        parts = []
        if days > 0:
            parts.append(f"{days} día(s)" if days == 1 else f"{days} días")
        if hours > 0:
            parts.append(f"{hours} hora(s)" if hours == 1 else f"{hours} horas")
        if minutes > 0:
            parts.append(f"{minutes} min")
        parts.append(f"{seconds} seg")
        return ", ".join(parts)
    except Exception:
        return "Desconocido"


def get_pc_status_message() -> str:
    hostname = socket.gethostname()
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    uptime_str = get_system_uptime()

    return (
        "💻 Estado del PC / Servidor:\n\n"
        "✅ Este PC está encendido y el bot está activo.\n"
        f"🖥️ Equipo: {hostname}\n"
        f"⏱️ Tiempo encendido: {uptime_str}\n"
        f"📅 Fecha y hora: {now_str}"
    )


def is_authorized(update: Update) -> bool:
    return bool(
        AUTHORIZED_CHAT_ID
        and update.effective_chat
        and str(update.effective_chat.id) == AUTHORIZED_CHAT_ID
    )


import html
import re


def format_telegram_html(text: str) -> str:
    escaped = html.escape(text)
    escaped = escaped.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    escaped = re.sub(r"&lt;a href=&quot;(.*?)&quot;&gt;", r'<a href="\1">', escaped)
    escaped = re.sub(r"&lt;a href=&#x27;(.*?)&#x27;&gt;", r'<a href="\1">', escaped)
    escaped = escaped.replace("&lt;/a&gt;", "</a>")
    return escaped


async def send_output(update: Update, output: str, success: bool) -> None:
    if not update.message:
        return

    clean_out = output.strip() or "El script terminó sin entregar salida."
    has_error_text = "[ERROR]" in clean_out or "Error:" in clean_out or "El script terminó con código" in clean_out
    is_success = success and not has_error_text

    prefix = "✅ Proceso completado con éxito:\n\n" if is_success else "❌ Se detectaron errores durante el proceso:\n\n"
    final_text = prefix + clean_out
    html_formatted = format_telegram_html(final_text)

    for start in range(0, len(html_formatted), 3900):
        chunk = html_formatted[start : start + 3900]
        try:
            await update.message.reply_text(chunk, parse_mode="HTML")
        except Exception:
            await update.message.reply_text(chunk)


async def run_script(script_name: str, arguments: list[str]) -> str:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(BASE_DIR / script_name),
        *arguments,
        cwd=BASE_DIR,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await process.communicate()
    output = stdout.decode("utf-8", errors="replace")
    if process.returncode:
        return f"El script terminó con código {process.returncode}.\n{output}"
    return output


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    help_text = (
        "🤖 <b>Menú de Comandos Disponibles:</b>\n\n"
        "1️⃣ <b>/verificar &lt;departamento&gt;</b>\n"
        "   └ Verifica la conexión y estado del router del departamento indicado.\n"
        "   <i>Ejemplo:</i> <code>/verificar 6</code>\n\n"
        "2️⃣ <b>/passwords [departamento]</b>\n"
        "   └ Obtiene la contraseña y URL del router de un departamento (o de todos si se omite).\n"
        "   <i>Ejemplo:</i> <code>/passwords 6</code> o <code>/passwords</code>\n\n"
        "3️⃣ <b>/cambiarpass &lt;departamento&gt; &lt;nueva_clave&gt;</b>\n"
        "   └ Cambia la contraseña Wi-Fi del departamento (mínimo 8 caracteres).\n"
        "   <i>Ejemplo:</i> <code>/cambiarpass 6 clave1234</code>\n\n"
        "4️⃣ <b>/estado</b> (o /pc, /ping, /encendido)\n"
        "   └ Verifica si el PC/Servidor está encendido, mostrando tiempo activo (Uptime).\n\n"
        "5️⃣ <b>/help</b> (o /ayuda, /start)\n"
        "   └ Muestra esta lista de comandos de ayuda.\n\n"
        "💡 <i>Tip: Al tocar o hacer clic sobre cualquier contraseña en los resultados, se copiará automáticamente al portapapeles.</i>"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await help_command(update, context)


async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    msg = get_pc_status_message()
    await update.message.reply_text(msg)


async def verificar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /verificar 6")
        return

    await update.message.reply_text(f"Verificando departamento {context.args[0]}...")
    output = await run_script("verificarConexion.py", [context.args[0]])
    await send_output(update, output, not output.startswith("El script terminó con código"))


async def cambiar_password(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not is_authorized(update):
        return
    if (
        len(context.args) != 2
        or not context.args[0].isdigit()
        or len(context.args[1]) < 8
    ):
        await update.message.reply_text("Uso: /cambiarpass <departamento> <clave de mínimo 8 caracteres>\nEjemplo: /cambiarpass 6 clave1234")
        return

    apartment_id, new_password = context.args
    await update.message.reply_text(
        f"Cambiando la contraseña del departamento {apartment_id}..."
    )
    output = await run_script("updatePassword.py", [apartment_id, new_password])
    await send_output(update, output, not output.startswith("El script terminó con código"))


async def passwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    dept_arg = context.args[0] if context.args else ""
    msg = f"Obteniendo contraseña del departamento {dept_arg}..." if dept_arg else "Obteniendo contraseñas..."
    await update.message.reply_text(msg)
    output = await run_script("obtenerPasswords.py", [dept_arg] if dept_arg else [])
    await send_output(update, output, not output.startswith("El script terminó con código"))


async def post_init(application: Application) -> None:
    from telegram import BotCommand
    commands = [
        BotCommand("help", "Ver comandos de ayuda"),
        BotCommand("estado", "Verificar si el PC está encendido"),
        BotCommand("passwords", "Obtener contraseñas de departamentos"),
        BotCommand("verificar", "Verificar estado de red de un depto"),
        BotCommand("cambiarpass", "Cambiar contraseña de un depto"),
    ]
    try:
        await application.bot.set_my_commands(commands)
    except Exception as e:
        print(f"Aviso al configurar menú de comandos: {e}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--status", "status", "--pc", "pc", "--estado", "estado"):
        print(get_pc_status_message())
        return

    if not BOT_TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en .env")
    if not AUTHORIZED_CHAT_ID:
        raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")

    print("🤖 Bot de Telegram iniciado y escuchando eventos...")
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("verificar", verificar))
    application.add_handler(CommandHandler("cambiarpass", cambiar_password))
    application.add_handler(CommandHandler("passwords", passwords))
    application.add_handler(CommandHandler("estado", estado))
    application.add_handler(CommandHandler("pc", estado))
    application.add_handler(CommandHandler("ping", estado))
    application.add_handler(CommandHandler("encendido", estado))
    application.run_polling()


if __name__ == "__main__":
    main()

