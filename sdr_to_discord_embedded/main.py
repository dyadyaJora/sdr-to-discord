import os
from dotenv import load_dotenv
from controllers.discord_bot_application import DiscordBotApplication


if __name__ == "__main__":
    load_dotenv()
    clientId = os.getenv('BOT_CLIENT_TOKEN')
    ffmpegPath = os.getenv('FFMPEG_PATH')
    DiscordBotApplication(clientId, ffmpegPath).start()
