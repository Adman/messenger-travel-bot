import os
import sys
import json

import imhdsk
import cpsk

import requests
from flask import Flask, request

app = Flask(__name__)


def send_message(recipient_id, message_text):
    log('to {recipient}: {text}'.format(recipient=recipient_id,
                                        text=message_text))

    params = {
        'access_token': os.environ['PAGE_ACCESS_TOKEN']
    }
    headers = {
        'Content-Type': 'application/json'
    }
    data = json.dumps({
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message_text
        },
        'tag': 'NON_PROMOTIONAL_SUBSCRIPTION'
    })
    r = requests.post('https://graph.facebook.com/v2.6/me/messages',
                      params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def split_args_by(args, by):
    return list(map(lambda x: x.strip(), args.split(by)))


def generate_output(nick, dep, dest, date, result=None):
    out = 'Nothing found'

    if len(result) >= 1:
        out = result[0].__repr__()

    return out


# taken from
# https://github.com/errbotters/err-sktravel/blob/master/sktravel.py#L70
def mhd(nick, args):
    if '-' in args:
        args = split_args_by(args, '-')
    else:
        args = args.split(' ')

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
    try:
        lower = msg.lower()
        if lower.startswith('vlak '):
            out = get_line(sender_id, msg[5:], 'vlak')
        elif lower.startswith('bus '):
            out = get_line(sender_id, msg[4:], 'bus')
        elif lower.startswith('spoj '):
            out = get_line(sender_id, msg[5:], 'vlakbus')
        elif lower.startswith('mhd '):
            out = mhd(sender_id, msg[4:])
        elif lower.startswith('help'):
            out = 'vlak/bus/mhd/spoj <from> - <to> - [time] - [date]'
    except:
        out = 'Failed to retrieve data.'

    send_message(sender_id, out)


@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    log(data)

    if data['object'] == 'page':
        for entry in data['entry']:
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    if messaging_event.get('message'):
                        sender_id = messaging_event['sender']['id']
                        message_text = messaging_event['message']['text']

                        response(sender_id, message_text)

    return 'ok', 200


@app.route('/', methods=['GET'])
def verify():
    if 'hub.challenge' in request.args:
        if not request.args.get('hub.verify_token') == os.environ['VERIFY_TOKEN']:
            return 'Verification token mismatch', 403
        return request.args['hub.challenge'], 200

    return 'travel bot page - privacy policy at /privacy', 200


@app.route('/privacy', methods=['GET'])
def privacy():
    out = 'We do not collect any profile info, user data or cookies.'
    return out, 200


def log(message):
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
