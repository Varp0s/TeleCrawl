import sys
from telethon.sync import TelegramClient


class TelegramSessionCreator:
    def __init__(self, api_id, api_hash):
        self.client = TelegramClient('telegramcrawler', api_id, api_hash)

    def create_session(self):
        with self.client as client:
            client.start()
            return client.session.save()

if __name__ == "__main__":
    api_id = input("Enter your API ID: ")
    api_hash = input("Enter your API Hash: ")

    creator = TelegramSessionCreator(api_id, api_hash)
    session_string = creator.create_session()
