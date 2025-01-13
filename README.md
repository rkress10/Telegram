# Telegram
How to use: clone the repo and go to the root folder

Run "python3 telegram.py" in the command line

It will ask "Verbose?". If you enter "Y" then you'll get a lot of logging

It will ask "Update data?". When you enter "Y", we will update the last seen message ID to prevent reprocessing messages.

It will then ask "Load Users?". If you reply with "Load Users" then we will pull all the users in the chat and re populate the users table. You shouldn't need to do this often (ever)

It will output the CSV file in the CSV folder, with the name in the format of 

GGOSightings_{date and time of the run}_{newest processed message id}_{oldest processed message id}


12696
