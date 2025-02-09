from telethon import TelegramClient
from telethon.tl.types import MessageMediaGeo, MessagePeerReaction
import json
import requests
import validators
import bs4
from urllib.parse import urlparse
from urllib.parse import parse_qs
import datetime
import re

api_id = "25573622"
api_hash = "a96beeca7659b9911511d819448cb247"
client = TelegramClient('anon', api_id, api_hash)
client.start()
dataCsv = []
lastReadMessageId = -1
firstReadMessageId = -1

verbose = False

targetSpecies = 'GGO'

#region constants
#region File constants
lastMessageFileName = "Database/lastMessageId"
ggoSightingsFileName = "Database/GGOSightings"
usersFileName = 'Database/Users'
martenFileName = 'CSV/MartenTimes.csv'
#endregion
_latLongconst = 'latlong'
_pendingconst = 'pending'
timeFormat = "%H:%M"
regExCoordinateString = '((\-?|\+?)?\d+(\.\d+)?),\s*((\-?|\+?)?\d+(\.\d+)?)'
#endregion

def TimeToKeyString(inTime):
    minute = int(inTime.minute)
    hour = int(inTime.hour)
    if minute >= 45:
        hour += 1
        minute = 0
    elif minute >= 15:
        minute = 30
    else:
        minute = 0
    return datetime.datetime(2025,1,1,hour % 24, minute, 0).strftime(timeFormat)

def UTCToCentral(utcTime):
    newTime = str((int(utcTime[:2]) + 18) % 24) + utcTime[2:]
    Log(f'{utcTime},{newTime}')
    return newTime

async def ParseMartenTimes():
    channel = await client.get_entity(-1001221913118)
    minNum = 0000
    #minNum = 11800
    tot = 0
    f = open(martenFileName, 'w')
    halfHour = {}
    keyString = ''
    async for message in client.iter_messages(channel, min_id = minNum):
        tot += 1
        if message.action != None or message.from_id == None:
            # these are mostly users joining the channel, ignore
            continue
        elif "marten" in message.message.lower() or "martin" in message.message.lower():
            if "feeder" in message.message.lower():
                keyString = TimeToKeyString(message.date)
                if keyString in halfHour:
                    halfHour[keyString] += 1
                else:
                    halfHour[keyString] = 1
    tmpTime = datetime.datetime(2025,1,1,6,0,0)
    maxTime = datetime.datetime(2025,1,1,23,59,59)
    while tmpTime < maxTime:
        keyString = TimeToKeyString(tmpTime)
        outputString = UTCToCentral(keyString)
        if keyString in halfHour:
            f.write(f'{outputString}, {halfHour[keyString]}\n')
        else:
            f.write(f'{outputString}, 0\n')
        timeChange = datetime.timedelta(minutes=30)
        tmpTime = tmpTime + timeChange
    f.close()
    print(f'Read {tot} messages')
        
async def ParseGGOSightings():
    channel = await client.get_entity(-1001221913118)
    updateData = input("Update Data?: ")
    minMessageId = 0
    if updateData != "historical":
        minMessageId = TryGetLastMessageId(updateData)
    Log(f'Starting at message: {minMessageId}')
    sightingsData = {}
    isFirst = True
    lastReadMessageId = -1
    firstReadMessageId = -1
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
            Log(firstReadMessageId)
            if updateData == "Y":
                UpdateLastReadMessage(firstReadMessageId)
        if message.action != None or message.from_id == None:
            # these are mostly users joining the channel, ignore
            continue
        if type(message.media) == MessageMediaGeo:
            HandleAppleMaps(message, sightingsData)
        elif 'maps.app.goo.gl' in message.message:
            HandleGoogleMaps(message, sightingsData)
        elif ContainsTargetSpecies(message.message) and ContainsCoordinates(message.message):
            c = SanitizeCoordinates(ContainsCoordinates(message.message).group())
            AddToCsv(c, GetUserId(message), message.date)
        elif ContainsCoordinates(message.message):
            coordinates = SanitizeCoordinates(ContainsCoordinates(message.message).group())
            HandleFoundCoordinates(message, coordinates, sightingsData)
            Log(f'{message.message}, {coordinates}')
        elif ContainsTargetSpecies(message.message):
            HandleSighting(message, sightingsData)
        elif GetUserId(message) in sightingsData:
            if len(sightingsData[GetUserId(message)][_latLongconst]) > 0:
                sightingsData[GetUserId(message)][_latLongconst].pop()
                Log('Not Added to CSV')
    OutputCSV(users, firstReadMessageId, lastReadMessageId)

def SanitizeCoordinates(coord):
    tmp = coord.split(',')
    return f'{tmp[0]} N, {abs(float(tmp[1].strip()))} W'

def ContainsCoordinates(messageString):
    return re.search(regExCoordinateString, messageString)

def ContainsTargetSpecies(messageString):
    if targetSpecies == 'GGO':
        return ContainsGGO(messageString)
    elif targetSpecies == 'Boreal':
        return ContainsBoreal(messageString)
    else:
        return False

def ContainsGGO(messageString):
    return 'GGO' in messageString.upper() or 'great grey' in messageString.lower() or 'great gray' in messageString.lower()

def ContainsBoreal(messageString):
    return 'boreal owl' in messageString.lower()

def OutputCSV(users, firstReadMessageId, lastReadMessageId):
    if len(dataCsv) == 0:
        Log('No sightings')
        return
    f = open(f'CSV/{targetSpecies}Sightings_{datetime.datetime.now()}_{lastReadMessageId}_{firstReadMessageId}.csv', 'w')
    for row in dataCsv:
        splitRow = row.split(',')
        username = 'Unknown'
        Log(splitRow)
        if splitRow[2] in users:
            username = users[splitRow[2]]
        date = splitRow[3]
        utcTime = splitRow[4]
        localHour = (int(utcTime[:2]) - 6) % 12
        utcTime = str(localHour) + utcTime[2:]
        f.write(f'{date},"{splitRow[0]}, {splitRow[1]}",{username},{utcTime}')
        f.write('\n')
    f.close()

def Log(message):
    if verbose:
        print(message)

async def LoadUsers2(channel):
    users = await client.get_participants(channel)
    f = open(usersFileName, 'w')
    userMap = {}
    for user in users:
        Log(user)
        userMap[str(user.id)] = f'{user.first_name} {user.last_name}'
    json.dump(userMap, f)
    f.close()

def LoadUsers():
    f = open(usersFileName, 'r')
    users = json.loads(f.read())
    f.close()
    return users

def HandleSighting(message, sightingsData):
    Log(message.message)
    userId = GetUserId(message)
    if userId not in sightingsData:
        # Add user to sightings
        sightingsData[userId] = {}
        sightingsData[userId][_latLongconst] = []
        sightingsData[userId][_pendingconst] = True
    else:
        if len(sightingsData[userId][_latLongconst]) > 0:
            AddToCsv(sightingsData[userId][_latLongconst][-1], userId, message.date)
            sightingsData[userId][_latLongconst].pop()
            sightingsData[userId][_pendingconst] = False
        else:
            sightingsData[userId][_pendingconst] = True

def HandleAppleMaps(message, sightingsData):
    latLong = FormatAppleMaps(message.media.geo)
    Log(f'apple maps: {latLong}')
    HandleFoundCoordinates(message, latLong, sightingsData)

def HandleGoogleMaps(message, sightingsData):
    latLong = FormatGoogleMaps(message.message)
    if latLong == None:
        return
    Log(f'google maps: {latLong}')
    HandleFoundCoordinates(message, latLong, sightingsData)

def HandleFoundCoordinates(message, latLong, sightingsData):
    userId = GetUserId(message)
    if userId in sightingsData and sightingsData[userId][_pendingconst]:
        AddToCsv(latLong, userId, message.date)
        sightingsData[userId][_pendingconst] = False
    else:
        AddToSightingsList(latLong, GetUserId(message), sightingsData)

def AddToCsv(latLong, userId, datetime):
    date = datetime.strftime("%m/%d/%Y")
    time = datetime.strftime("%H:%M:%S")
    dataCsv.append(f'{latLong},{userId},{date},{time}')
    Log('Added to CSV')

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
        Log(f'Invalid URL: {originalUrl}')
        return
    x = requests.get(url)
    html = bs4.BeautifulSoup(x.text, features='html5lib')
    try:
        latLong = parse_qs(urlparse(html.title.text).query)['q'][0].split(',')
        return FormatLatLong(latLong[0], latLong[1])
    except:
        Log(f'Could not use URL {originalUrl}')
        return

def FormatLatLong(lat, long):
    return f'{lat} N, {abs(float(long))} W'

def TryGetLastMessageId(updateData):
    try:
        f = open(lastMessageFileName, "r")
        lastReadMessageIds = json.loads(f.read())
        f.close()
        return lastReadMessageIds["prod"] if updateData=="Y" else lastReadMessageIds["test"]
    except:
        print("Error getting the last read message ID")
        return -1
    
def UpdateLastReadMessage(messageId):
    try:
        f = open(lastMessageFileName, "r")
        newIds = json.loads(f.read())
        f.close()
        newIds["prod"] = messageId
        f = open(lastMessageFileName, "w")
        json.dump(newIds, f)
        f.close()
        Log(f"Updated last read message: {messageId}")
    except Exception as e:
        print(e)
        print("Problem saving the last read message")

if __name__ == "__main__":
    verbose = input("Verbose?: ") == "Y"
    animal = input("M for marten: ")
    if (animal == "M"):
        with client:
            client.loop.run_until_complete(ParseMartenTimes())
    else:
        with client:
            client.loop.run_until_complete(ParseGGOSightings())