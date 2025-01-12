import requests
from telethon import TelegramClient
from telethon.tl import functions, types

api_id = "25573622"
api_hash = "a96beeca7659b9911511d819448cb247"
client = TelegramClient('anon', api_id, api_hash)
client.start()

#region File constants
lastMessageFileName = "Database/lastMessageId"
#endregion

async def main():
    channel = await client.get_entity(-1001221913118)
    minMessageId = TryGetLastMessageId()
    if minMessageId == -1:
        return
    async for message in client.iter_messages(channel, min_id = minMessageId):
        print(message.id, message.date)
        continue
        if message.action != None:
            continue
        print(message)
        if message.media != None:
            print('a')
            print('apple maps', message.media)
        elif 'GGO' in message.message:
            print('b')
            print(message.message)
        elif 'maps.app.goo.gl' in message.message:
            print('c')
            print('google maps', message.message)

def TryGetLastMessageId():
    try:
        f = open(lastMessageFileName, "r")
        return int(f.read())
    except:
        print("Error getting the last read message ID")
        return -1



with client:
    client.loop.run_until_complete(main())