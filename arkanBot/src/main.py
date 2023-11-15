from telegram.ext import (
    # Updater,
    MessageHandler,
    filters,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)
from glob import glob
import os
import time
from telegram import Update
import logging
import dateparser
import re
from dateparser.search.search import DateSearchWithDetection
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def parse_date(date_str):

    if parsed_date := dateparser.parse(date_str, languages=["ru"]):
        return parsed_date.date()
    else:
        return None


def generate_pdf_path(arcan):
    pdf_directory = "../misk/"
    if pdf_files := glob(os.path.join(pdf_directory, f"{arcan}_*.pdf")):
        return pdf_files[0]
    else:
        return None


async def send_arcan(update: Update, context: ContextTypes.DEFAULT_TYPE, arcan):
    if pdf_path := generate_pdf_path(arcan):
        with open(pdf_path, "rb") as pdf_file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_file,
                # caption=f"Ваш аркан: {arcan}",
                caption="",
            )


def calculate_arcan(date):
    # Расчет аркана
    return date if date < 22 else date - 22


def extract_digit_substring(input_string):
    if matches := re.findall(r"\d+", input_string):
        start_index = input_string.index(matches[0])
        end_index = input_string.rindex(matches[-1]) + len(matches[-1])
        return input_string[start_index:end_index]
    else:
        return input_string


def first_try_pars(message):
    maybe_date = extract_digit_substring(message)
    # if maybe_date is None:
    #     return None
    res = parse_date(maybe_date)
    if res is None:
        res = parse_date(message)
    return res


def second_try_pars(message: str):
    _search_with_detection = DateSearchWithDetection()
    result = _search_with_detection.search_dates(message, languages=["ru"])
    result = result.get("Dates")
    if result == [] or result is None:
        return None
    birth_date = replace_shit_from_string(str(result[0][1]))
    print(f"BIRTH DATE ={birth_date}")
    return birth_date


def replace_shit_from_string(str: str):
    return (
        str.replace("-", "")
        .replace(" ", "")
        .replace(":", "")
        .replace("0", "")
        .replace(",", "")
    )


async def handle_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    message = update.message.text
    birth_date = first_try_pars(message)
    is_robot_sure = ""
    if birth_date is None:
        is_robot_sure = "Я не уверен и скорее всего ошибаюсь, но возможно это правильный аркан, лучше проверь: "
        birth_date = second_try_pars(message)
    else:
        birth_date = replace_shit_from_string(str(birth_date))
    if birth_date:
        date_sum = sum(int(digit) for part in birth_date for digit in part)
        arcan = calculate_arcan(date_sum)
        increment_arcana_counter(update, context, arcan)
        if not is_robot_sure:
            increment_counter(update, context, "success_count")
        else:
            increment_counter(update, context, "failure_count")

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{is_robot_sure}{user.first_name}, ваш аркан: {arcan}",
        )
        await send_arcan(update, context, arcan)
    else:

        increment_counter(update, context, "failure_count")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Прости, {user.first_name}, но мне не удалось определить дату рождения.",
        )


def increment_counter(
    update: Update, context: ContextTypes.DEFAULT_TYPE, counter_name: str
):
    chat_id = update.effective_chat.id
    context.bot_data.setdefault(counter_name, {}).setdefault(chat_id, 0)
    context.bot_data[counter_name][chat_id] += 1


def get_counter(update: Update, context: ContextTypes.DEFAULT_TYPE, counter_name):
    chat_id = update.effective_chat.id
    return context.bot_data.get(counter_name, {}).get(chat_id, 0)


def increment_arcana_counter(update: Update, context: ContextTypes.DEFAULT_TYPE, arcan):
    chat_id = update.effective_chat.id
    context.bot_data.setdefault("arcana_counter", {}).setdefault(
        chat_id, {}
    ).setdefault(arcan, 0)
    context.bot_data["arcana_counter"][chat_id][arcan] += 1


def get_arcana_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    return context.bot_data.get("arcana_counter", {}).get(chat_id, {})


async def handle_get_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    win = get_counter(update, context, "success_count")
    lose = get_counter(update, context, "failure_count")
    arcana_stat = get_arcana_stat(update, context)
    stat = "" if arcana_stat == {} else "Вот статистика по арканам:\n"
    text = f"""Я уже успешно распознал арканов: {win} \nНо было и несколько уродских сообщений: {lose} \n{stat}"""
    for arcan, count in arcana_stat.items():
        text += f"{arcan} аркан = {count}\n"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


if __name__ == "__main__":
    while True:

        try:
            try:
                application = ApplicationBuilder().token(TOKEN).build()
            except Exception as er:
                logging.error(f"APP ERR ={er}")
                # exit(0)
                continue
            # Обработка сообщений с датой рождения
            application.add_handler(
                MessageHandler(filters.TEXT & (~filters.COMMAND), handle_birthday)
            )
            # Обработка статистики
            application.add_handler(CommandHandler("getStat", handle_get_stat))
            try:
                application.run_polling(
                    timeout=100
                )  # Увеличиваем время ожидания до 60 секунд
            except Exception as er:
                logging.error(f"polling er ={er}")
                time.sleep(5)
                continue
        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
