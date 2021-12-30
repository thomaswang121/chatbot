#! /bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

LOCKFILE=/tmp/chat-shell-script.lock
if [ -f $LOCKFILE ]
then
    echo "shell script already running!"
    exit
fi


#Create lock file
echo '' > ${LOCKFILE}

if [ ! -f $LOCKFILE ]
then
    echo "create lock file failed!"
    exit
fi

# Main
cd ~/Desktop/chatbot/
source env/bin/activate
cd ~/Desktop/chatbot/demo
python3 ~/Desktop/chatbot/demo/scraper.py
date -R >> time.log
error=${?}
echo "scraper to db:"${error} >> time.log
while [ "$error" -ne "0" ]
do
    sleep 30
    python3 ~/Desktop/chatbot/demo/scraper.py
    date -R >> time.log
    error=${?}
    echo "scraper to db:"${error} >> time.log
done

# Remove lock file
rm -f ${LOCKFILE}
