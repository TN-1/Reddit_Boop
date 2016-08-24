import praw, datetime, time, random, gspread, sys
from oauth2client.service_account import ServiceAccountCredentials
from prawoauth2 import PrawOAuth2Mini

# Get some variables setup
today = str(datetime.datetime.now().day) + "-" + str(datetime.datetime.now().month) + "-" + str(datetime.datetime.now().year)
scopes = ['flair', 'modcontributors', 'modflair', 'modposts', 'history', 'posts', 'sumbit']
subreddit = "" # Your sub's name without the /r/
# Replace the following ouath settings with your own
access_token = ""
refresh_token = ""
app_key = ""
app_secret = ""

def log(m, show=True):
    logs = open("logs"+ today +".txt", "a")
    logs.write(m + "\n")

    if show==True:
        print m

    logs.close()

# Bot login
log("Signing in to reddit...")
r = praw.Reddit(user_agent="Reddit kick and add bot. Maintained by github.com/TN-1")
oauth_helper = PrawOAuth2Mini(r, app_key=app_key, app_secret=app_secret, access_token=access_token, refresh_token=refresh_token, scopes=scopes)
s = praw.objects.Subreddit(r,subreddit) # Add your subreddit here
log("Done")

# Sheets login
# This section is used to log into google sheets to fetch flair settings.
# scope = ['https://spreadsheets.google.com/feeds']
# credentials = ServiceAccountCredentials.from_json_keyfile_name('', scope) # You need a json file from Google API to add here
# gc = gspread.authorize(credentials)
# log("Accessed Docs API")
# flagsheet = gc.open("").sheet1 # Spreadsheet name
# log("Accessed flairs sheet")

# Setting up initial parameters
immunity = [] # Usernames of users to not consider for kicking
memberCap = 100 # How many users in the sub?
bannedSubs = [] # Subreddits we dont want to find users in
bannedUsers = [] # Users we dont want in our sub
karmaDownLimit = 100  # Minimum comment karma
karmaUpLimit = 100000  # Maximum comment karma
accountAgeLimit = 90 # Minimum account age in days
wordsLimit = []  # Words we don't want in a username
recap = ""

# You shouldnt need to edit anything below here unless you are enabling flairs
# Find out what we should do today
runmode = input('0 for full bot run, 1 for kick only, 2 for Flair refresh, 3 for Python Install Verification\n')


# functions
def kick(user):
    s.remove_contributor(user)
    flair(user,"[Kicked]",'kicked')
    log("Kicked " + user)

def add(user):
    s.add_contributor(user)
    log("Added " + user)

def getUserList():
    userList = []
    req = r.get_contributors(subreddit,limit=None)
    for u in req:
        username = str(u)
        if username != "": # Username of the bot
            userList.append(username)
    userList.reverse()
    return userList

def flair(user,flair,css):
    s.set_flair(user, flair,flair_css_class=css)
    log("/u/"+user+"'s flair changed to '"+flair+"' (CSS "+css+")")

def postRecap(m):
    log("Posting the recap...")
    if runmode == 0:
        postTitle = str(today) +' - Bot Recap'
    elif runmode == 1:
        postTitle = str(today) +' - Bot Recap(Kick only)'
    r.submit(subreddit, postTitle, m).distinguish()
    log("Done")
    sys.exit

def getFlair(user):
    number = "number"
    #Uncommment the following lines to enable google sheets flair
    #log("Searching sheets for flag for " + user)
    #try:
        # cell = flagsheet.find(user)
        # flag = flagsheet.cell(cell.row, 2).value
        # log("Found a flag. Flag is " + str(flag))
        # return flag
    #except:
        # log("No flag found. Assign class number")
        # return number
    return number

if runmode == 0:
    log("Run mode 0: Full Boop")
    # Kicking
    memberList = getUserList()
    recap += "Kicked users:  \n"

    log("Starting to kick inactive members...")

    i = 0
    n = 0

    for member in memberList:
        i+=1
        log("#" + str(i) + " /u/" + member)

        if member in immunity:
            log("/u/" + member + " is in immunity list.")
            continue


        overview = r.get_redditor(member).get_overview(limit=None)

        latestPost = 50000.0 #hours
        hoursLimit = 180.0 #hours

        for post in overview:
            postedSub = post.subreddit.display_name
            hoursAgo = (time.time()-post.created_utc)/3600.0

            if postedSub == subreddit:
                if hoursAgo < latestPost:
                    latestPost = hoursAgo

            if hoursAgo>hoursLimit:
                break

        if latestPost <= hoursLimit:
            log("[OK] Latest post was " + str(latestPost) + " hours ago.")
        else:
            log("[NOT OK] No post in /r/%s in the last 7 days." % subreddit)
            recap += "\#" + str(i) + " - /u/" + member + "\n\n"
            n+=1
            kick(member)

    #Adding
    comments = r.get_comments("all",limit=None)
    nbAdded = memberCap-len(memberList)+n
    newUser = ""
    log("Adding " + str(nbAdded) + " users...")
    newUser = ""
    recap += "\nAdded users:  \n\n"

    if nbAdded<0:
        nbAdded=0

    while nbAdded>0:
        for c in comments:
            username = str(c.author)
            linkId = c.link_id.replace("t3_","")+"/"+c.id
            karma = c.author.comment_karma
            postedSub = c.subreddit.display_name
            accountAge = (time.time()-c.author.created_utc)/86400.0

            log("Considering /u/" + username + " from post " + linkId + ".")

            if username in bannedUsers:
                log("[NOT OK] Banned user.")
                continue

            if postedSub in bannedSubs:
                log("[NOT OK] Posted in a banned subreddit")
                continue

            if karma < karmaDownLimit:
                log("[NOT OK] Comment karma too low.")
                continue

            if karma > karmaUpLimit:
                log("[NOT OK] Comment karma too high.")
                continue

            if accountAge < accountAgeLimit:
                log("[NOT OK] Account too recent.")
                continue

            if any(word in username for word in wordsLimit):
                log("[NOT OK] Username contains banned word.")
                continue

            if random.randint(0,1) == 1:
                log("[NOT OK] Not lucky enough.")
                continue

            nbAdded-=1

            print nbAdded
            add(username)

            if newUser == "":
                newUser = username

            if nbAdded==0:
                break

    new=""
    i=0
    for user in getUserList():
        i+=1
        if user==newUser:
            new="new"

        if new=="new":
            flair(user,'#'+str(i),'number'+new)
            recap += "\#" + str(i) + " - /u/" + user + "\n\n"
        else:
            flagcss = getFlair(user)
            flair(user,'#'+str(i),flagcss)

    #Post the recap
    postRecap(recap)

elif runmode == 1:
    log("Run mode 1: Kick Boop")
    # Kicking
    memberList = getUserList()
    recap += "Kicked users:  \n"

    log("Starting to kick inactive members...")

    i = 0
    n = 0

    for member in memberList:
        i+=1
        log("#" + str(i) + " /u/" + member)

        if member in immunity:
            log("/u/" + member + " is in immunity list.")
            continue


        overview = r.get_redditor(member).get_overview(limit=None)

        latestPost = 50000.0 #hours
        hoursLimit = 180.0 #hours

        for post in overview:
            postedSub = post.subreddit.display_name
            hoursAgo = (time.time()-post.created_utc)/3600.0

            if postedSub == subreddit:
                if hoursAgo < latestPost:
                    latestPost = hoursAgo

            if hoursAgo>hoursLimit:
                break

        if latestPost <= hoursLimit:
            log("[OK] Latest post was " + str(latestPost) + " hours ago.")
        else:
            log("[NOT OK] No post in /r/%s in the last 7 days." % subreddit)
            recap += "\#" + str(i) + " - /u/" + member + "\n\n"
            n+=1
            kick(member)

    i=0
    for user in getUserList():
        i+=1
        flagcss = getFlair(user)
        flair(user,'#'+str(i),flagcss)

    #Post the recap
    postRecap(recap)

elif runmode == 2:
    log("Run mode 2: Flair Update")
    i=0
    for user in getUserList():
        i+=1
        flagcss = getFlair(user)
        flair(user,'#'+str(i),flagcss)

elif runmode == 3:
    log("Run mode 3: Install Verify")
    i=0
    for user in getUserList():
        i+=1
        log("/u/"+user+" #"+str(i))
else:
    log("No run mode specified. Ending")
    sys.exit
