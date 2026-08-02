import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
AUTHORIZED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def is_authorized(update: Update) -> bool:
    return bool(
        AUTHORIZED_CHAT_ID
        and update.effective_chat
        and str(update.effective_chat.id) == AUTHORIZED_CHAT_ID
    )


async def send_output(update: Update, output: str, success: bool) -> None:
    if not update.message:
        return

    prefix = "✅ Script finalizado correctamente.\n" if success else "❌ El script terminó con errores.\n"
    output = prefix + (output.strip() or "El script terminó sin entregar salida.")
    for start in range(0, len(output), 3900):
        await update.message.reply_text(output[start : start + 3900])


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/verificar <departamento>\n"
        "/cambiarpass <departamento> <clave de 6 dígitos>"
    )


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
        or not context.args[1].isdigit()
        or len(context.args[1]) != 6
    ):
        await update.message.reply_text("Uso: /cambiarpass 6 123456")
        return

    apartment_id, new_password = context.args
    await update.message.reply_text(
        f"Cambiando la contraseña del departamento {apartment_id}..."
    )
    output = await run_script("updatePassword.py", [apartment_id, new_password])
    await send_output(update, output, not output.startswith("El script terminó con código"))


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en .env")
    if not AUTHORIZED_CHAT_ID:
        raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verificar", verificar))
    application.add_handler(CommandHandler("cambiarpass", cambiar_password))
    application.run_polling()


if __name__ == "__main__":
    main()
