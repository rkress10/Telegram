# Telegram
How to use: clone the repo and go to the root folder
Run "python3 telegram.py" in the command line
It will ask "Update data?". When you enter "Y", we will update the last seen message ID to prevent reprocessing messages.
It will then ask "Load Users?". If you reply with "Load Users" then we will pull all the users in the chat and re populate the users table. You shouldn't need to do this often
It will output the CSV file in the CSV folder, with the name in the format of 
"GGOSightings_{newest processed message id}_{oldest processed message id}_{date and time of the run}
Once you have the CSV 


12696