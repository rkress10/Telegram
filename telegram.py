from telethon import TelegramClient
from telethon.tl.types import MessageMediaGeo, MessagePeerReaction
import json
import requests
import validators
import bs4
from urllib.parse import urlparse
from urllib.parse import parse_qs
import datetime

api_id = "25573622"
api_hash = "a96beeca7659b9911511d819448cb247"
client = TelegramClient('anon', api_id, api_hash)
client.start()
dataCsv = []
lastReadMessageId = -1
firstReadMessageId = -1

#region constants
#region File constants
lastMessageFileName = "Database/lastMessageId"
ggoSightingsFileName = "Database/GGOSightings"
usersFileName = 'Database/Users'
#endregion
_latLongconst = 'latlong'
_pendingconst = 'pending'
#endregion

async def main():
    channel = await client.get_entity(-1001221913118)
    updateData = input("Update Data?: ")
    minMessageId = TryGetLastMessageId(updateData)
    sightingsData = TryLoadSightings()
    isFirst = True
    if minMessageId == -1:
        return
    if input("Load Users?: ") == "Load Users":
        await LoadUsers2(channel)
    users = LoadUsers()
    async for message in client.iter_messages(channel, min_id = minMessageId):
        lastReadMessageId = message.id
        if isFirst:
            isFirst = False
            firstReadMessageId = message.id
        if message.action != None or message.from_id == None:
            # these are mostly users joining the channel, ignore
            continue
        if type(message.media) == MessageMediaGeo:
            HandleAppleMaps(message, sightingsData)
        elif 'maps.app.goo.gl' in message.message:
            HandleGoogleMaps(message, sightingsData)
        elif 'GGO' in message.message.upper() or 'great grey' in message.message.lower() or 'great gray' in message.message.lower():
            HandleGGO(message, sightingsData)
        elif GetUserId(message) in sightingsData:
            if len(sightingsData[GetUserId(message)][_latLongconst]) > 0:
                sightingsData[GetUserId(message)][_latLongconst].pop()
                print('Not Added to CSV 2')
        #print(sightingsData)
    print(dataCsv)
    OutputCSV(users)
    if updateData:
        UpdateLastReadMessage(lastReadMessageId)

def OutputCSV(users):
    f = open(f'CSV/GGOSightings_{firstReadMessageId}_{lastReadMessageId}_{datetime.datetime.now()}.csv', 'w')
    for row in dataCsv:
        splitRow = row.split(',')
        username = ''
        print(splitRow)
        if splitRow[2] in users:
            username = users[splitRow[2]]
        date = datetime.date.today()
        f.write(f'{date.month}/{date.day}/{date.year},"{splitRow[0]}, {splitRow[1]}",{username}')
        f.write('\n')
    f.close()

async def LoadUsers2(channel):
    users = await client.get_participants(channel)
    f = open(usersFileName, 'w')
    userMap = {}
    for user in users:
        print(user)
        userMap[str(user.id)] = f'{user.first_name} {user.last_name}'
    json.dump(userMap, f)
    f.close()

def LoadUsers():
    f = open(usersFileName, 'r')
    users = json.loads(f.read())
    f.close()
    return users

def HandleGGO(message, sightingsData):
    print(message.message)
    userId = GetUserId(message)
    if userId not in sightingsData:
        # Add user to sightings
        sightingsData[userId] = {}
        sightingsData[userId][_latLongconst] = []
        sightingsData[userId][_pendingconst] = True
    else:
        if len(sightingsData[userId][_latLongconst]) > 0:
            AddToCsv(sightingsData[userId][_latLongconst][-1], userId)
            sightingsData[userId][_latLongconst].pop()
            sightingsData[userId][_pendingconst] = False
        else:
            sightingsData[userId][_pendingconst] = True

def HandleAppleMaps(message, sightingsData):
    latLong = FormatAppleMaps(message.media.geo)
    print(f'apple maps: {latLong}')
    userId = GetUserId(message)
    if userId in sightingsData and sightingsData[userId][_pendingconst]:
        AddToCsv(latLong, userId)
        sightingsData[userId][_pendingconst] = False
    else:
        AddToSightingsList(latLong, GetUserId(message), sightingsData)

def HandleGoogleMaps(message, sightingsData):
    latLong = FormatGoogleMaps(message.message)
    if latLong == None:
        return
    print(f'google maps: {latLong}')
    userId = GetUserId(message)
    if userId in sightingsData and sightingsData[userId][_pendingconst]:
        AddToCsv(latLong, userId)
        sightingsData[userId][_pendingconst] = False
    else:
        AddToSightingsList(latLong, GetUserId(message), sightingsData)

def AddToCsv(latLong, userId):
    dataCsv.append(f'{latLong},{userId}')
    print('Added to CSV')

def AddToSightingsList(latLong, userId, sightingsData):
    if userId not in sightingsData:
        sightingsData[userId] = {}
        sightingsData[userId][_latLongconst] = []
        sightingsData[userId][_pendingconst] = False
    sightingsData[userId][_latLongconst].append(latLong)

def GetUserId(message):
    return message.from_id.user_id

def FormatAppleMaps(geo):
    return FormatLatLong(geo.lat, geo.long)

def FormatGoogleMaps(url):
    originalUrl = url
    if url[:3] == 'See':
        url = url[35:]
    if not validators.url(url):
        print(f'Invalid URL: {originalUrl}')
        return
    x = requests.get(url)
    html = bs4.BeautifulSoup(x.text, features='html5lib')
    try:
        latLong = parse_qs(urlparse(html.title.text).query)['q'][0].split(',')
        return FormatLatLong(latLong[0], latLong[1])
    except:
        print(f'Could not use URL {originalUrl}')
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

def TryGetLastMessageId(updateData):
    try:
        f = open(lastMessageFileName, "r")
        lastReadMessageIds = json.loads(f.read())
        f.close()
        return lastReadMessageIds["prod"] if updateData=="Y" else lastReadMessageIds["test"]
    except:
        print("Error getting the last read message ID")
        return -1
    
def UpdateLastReadMessage(lastReadMessageId):
    try:
        f = open(lastMessageFileName, "r")
        newIds = json.loads(f.read())
        f.close()
        newIds["prod"] = lastReadMessageId
        f.open(lastMessageFileName, "w")
        f.write(json.dump(newIds, f))
        f.close()
    except:
        print("Problem saving the last read message")

with client:
    client.loop.run_until_complete(main())