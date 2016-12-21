import os
import sys
import json
import datetime

import imhdsk
import cpsk

import requests
from flask import Flask, request

app = Flask(__name__)

searched = {}


@app.route('/', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "travel bot page", 200



def send_message(recipient_id, message_text):

    log("to {recipient}: {text}".format(recipient=recipient_id,
                                        text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def split_args_by(args, by):
    return list(map(lambda x: x.strip(), args.split(by)))


def generate_output(nick, dep, dest, date, result=None):
    out = 'Nothing found'

    if date == '':
        date = datetime.datetime.today().strftime('%d.%m.%Y')

    if len(result) >= 1:
        out = result[0].__repr__()
        obj = result[0]

        if hasattr(obj, 'lines') and len(obj.lines) >= 1:
            time = obj.lines[0].departure
        elif hasattr(result[0], 'drives') and len(obj.drives) >= 1:
            time = result[0].drives[0].begin_time
        searched[nick] = [dep, dest, time, date]

    return out


def searched_incrementer(nick):
    dep, dest, time, date = searched[nick]

    dateobj = datetime.datetime.strptime('{0}-{1}'.format(time,
                                                          date),
                                         '%H:%M-%d.%m.%Y')
    dateobj += datetime.timedelta(seconds=60)
    date = dateobj.strftime('%d.%m.%Y')
    time = dateobj.strftime('%H:%M')

    searched[nick] = [dep, dest, time, date]
    return searched[nick]


def rootify(self, word):
    if len(word) <= 5:
        return word

    w = word[::-1]
    vowels = ['a', 'e', 'i', 'o', 'u', 'y']
    for x in range(len(word)):
        if w[x] in vowels and x != 0:
            return word[:-(x + 1)]


def mhd(nick, args):
    if '-' in args:
        args = split_args_by(args, '-')
    else:
        args = args.split(' ')

    if len(args) >= 1 and args[0] == 'next':
        if nick not in searched:
            return 'No next line'
        args = searched_incrementer(nick)

    if len(args) < 2:
        return 'Not enough arguments specified. See help for usage'

    f = args[0]
    t = args[1]

    if f == t:
        return 'Not in this universe.'

    time = ''
    date = ''
    if len(args) >= 3:
        time = args[2]
    if len(args) >= 4:
        date = args[3]

    r = imhdsk.routes(f, t, time=time, date=date)
    return generate_output(nick, f, t, date, result=r)


# nick == sender_id
def get_line(nick, args, vehicle):
    if '-' in args:
        args = split_args_by(args, '-')
    else:
        args = args.split(' ')

    if len(args) >= 1 and args[0] == 'next':
        if nick not in searched:
            return 'No next line'
        args = searched_incrementer(nick)

    if len(args) < 2:
        return 'Not enough arguments specified. See help for usage'

    dep = args[0]
    dest = args[1]

    time = args[2] if len(args) > 2 else ''
    date = args[3] if len(args) > 3 else ''

    if dep == dest:
        return 'You joker'

    r = cpsk.get_routes(dep, dest, vehicle=vehicle, time=time, date=date)
    return generate_output(nick, dep, dest, date, result=r)


def response(sender_id, msg):
    out = 'Wrong command. Type help.'
    if msg.startswith('vlak '):
        out = get_line(sender_id, msg[5:], 'vlak')
    elif msg.startswith('bus '):
        out = get_line(sender_id, msg[4:], 'bus')
    elif msg.startswith('spoj '):
        out = get_line(sender_id, msg[5:], 'vlakbus')
    elif msg.startswith('mhd '):
        out = mhd(sender_id, msg[4:])
    elif msg.startswith('help'):
        out = 'vlak/bus/mhd/spoj <from> - <to> - [time] - [date]\nor vlak/bus/mhd/spoj next'

    send_message(sender_id, out)


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    log(data)

    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"] 
                    message_text = messaging_event["message"]["text"]

                    response(sender_id, message_text)

    return "ok", 200


def log(message):
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
