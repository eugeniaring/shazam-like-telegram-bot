import os
import json
import requests
import subprocess
import urllib.request 
from dotenv import load_dotenv
import time

from steamship import Steamship, TaskState
import telebot
from serpapi import GoogleSearch


## telegram bot
# f = open("cred.json", "rb")
# params = json.load(f)
# BOT_TOKEN = params['BOT_TOKEN']

load_dotenv()
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Insert the audio of your song!")


def convert_oga_to_mp3(audio_url):
    file = requests.get(audio_url)
    urllib.request.urlretrieve(audio_url,'audio.oga')
    subprocess.run(["ffmpeg", "-i", 'audio.oga', 'audio.mp3'])
    data = open('audio.mp3', 'rb')

def get_url_mp3(bot_token,message):
    bot.reply_to(message, 'Searching song...')
    data = open('audio.mp3', 'rb')
    ret_msg = bot.send_voice(message.chat.id,data)
    ret_msg.voice.file_id
    file_info = bot.get_file(ret_msg.voice.file_id)
    audio_url = 'https://api.telegram.org/file/bot{}/{}'.format(bot_token,file_info.file_path)
    return audio_url

# transcribe audio with Steamship's API
def transcribe_audio(audio_url: str, ship: Steamship):
    instance = ship.use("audio-markdown", "audio-markdown-crows-v27")
    transcribe_task = instance.invoke("transcribe_url", url=audio_url)
    task_id = transcribe_task["task_id"]
    status = transcribe_task["status"]

    # Wait for completion
    retries = 0
    while retries <= 100 and status != TaskState.succeeded:
        response = instance.invoke("get_markdown", task_id=task_id)
        status = response["status"]
        if status == TaskState.failed:
            print(f"[FAILED] {response}['status_message']")
            break

        print(f"[Try {retries}] Transcription {status}.")
        if status == TaskState.succeeded:
            break
        time.sleep(2)
        retries += 1

    # Get Markdown
    markdown = response["markdown"]
    return markdown

## search the trascription on Google using SerpAPI 
def search_words(words):
    params = {
    "q": words,
    "hl": "en",
    "gl": "us",
    "google_domain": "google.com",
    "api_key": os.getenv("API_KEY")
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    if 'organic_results' in results.keys():
        if 'title' in results['organic_results'][0].keys():
            return results['organic_results'][0]['title']
        else:
            return ''
    else:
        return ''
        
    

@bot.message_handler(content_types=['voice'])
def telegram_bot(message,bot_token=os.getenv("BOT_TOKEN")):
    client = Steamship(api_key=os.getenv("STEAM_TOKEN"))
    # insert audio
    file_info = bot.get_file(message.voice.file_id)
    # extract telegram's url of the audio 
    audio_url = 'https://api.telegram.org/file/bot{}/{}'.format(bot_token,file_info.file_path)
    
    convert_oga_to_mp3(audio_url)
    audio_url = get_url_mp3(bot_token,message)

    bot.enable_save_next_step_handlers(delay=2)
    markdown = transcribe_audio(audio_url, client)
    print(markdown)

    bot.reply_to(message, markdown)
    result = search_words(markdown)
    
    os.remove("audio.mp3")
    os.remove("audio.oga")

    if result == '':
        bot.reply_to(message, 'Song not found!')
    else:
         bot.reply_to(message, result)

bot.infinity_polling()

