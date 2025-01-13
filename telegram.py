from telethon import TelegramClient
from telethon.tl.types import MessageMediaGeo
import json
import requests
import validators
import bs4
from urllib.parse import urlparse
from urllib.parse import parse_qs

api_id = "25573622"
api_hash = "a96beeca7659b9911511d819448cb247"
client = TelegramClient('anon', api_id, api_hash)
client.start()

#region File constants
lastMessageFileName = "Database/lastMessageId"
ggoSightingsFileName = "Database/GGOSightings"
#endregion

async def main():
    channel = await client.get_entity(-1001221913118)
    useRealData = input("Update Data?: ")
    minMessageId = TryGetLastMessageId()
    sightingsData = TryLoadSightings()
    if minMessageId == -1:
        return
    async for message in client.iter_messages(channel, min_id = minMessageId):
        if message.action != None:
            # these are mostly users joining the channel, ignore
            continue
        if type(message.media) == MessageMediaGeo:
            a = FormatAppleMaps(message.media.geo)
            print(f'apple maps: {a} from: {message.from_id.user_id}')
            #sightingsData[message.from_id.user_id].append(a)
        elif 'GGO' in message.message:
            print(message.message)
        elif 'maps.app.goo.gl' in message.message:
            print(f'google maps: {FormatGoogleMaps(message.message)}')
    print(sightingsData)

def FormatAppleMaps(geo):
    return FormatLatLong(geo.lat, geo.long)

def FormatGoogleMaps(url):
    if url[:3] == 'See':
        url = url[35:]
    if not validators.url(url):
        print(f'Invalid URL: {url}')
        return
    x = requests.get(url)
    html = bs4.BeautifulSoup(x.text, features='html5lib')
    try:
        latLong = parse_qs(urlparse(html.title.text).query)['q'][0].split(',')
        return FormatLatLong(latLong[0], latLong[1])
    except:
        print(f'Could not use URL')
        return

def FormatLatLong(lat, long):
    return f'{lat} N, {abs(float(long))} W'

def TryLoadSightings():
    try:
        f = open(ggoSightingsFileName, "r")
        sightings = json.loads(f.read())
        f.close()
        return sightings
    except:
        print("Error loading sightings")
        return {}

def TryGetLastMessageId():
    try:
        f = open(lastMessageFileName, "r")
        lastReadMessageId = int(f.read())
        f.close()
        return lastReadMessageId
    except:
        print("Error getting the last read message ID")
        return -1
    
def UpdateLastReadMessage(lastReadMessageId):
    try:
        f = open(lastMessageFileName, "w")
        f.write(lastReadMessageId)
        f.close()
    except:
        print("Problem saving the last read message")

with client:
    client.loop.run_until_complete(main())