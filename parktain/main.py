#!/usr/bin/env python

# Standard library
from datetime import datetime
import json
from os.path import abspath, dirname, join
import re

# 3rd party library
from gendo import Gendo
from sqlalchemy.orm import sessionmaker

# Local library
from parktain.models import Base, Channel, engine, Message, User

Session = sessionmaker(bind=engine)
session = Session()

HERE = dirname(abspath(__file__))
URL_RE = re.compile('<(https{0,1}://.*?)>')

config_path = join(HERE, 'config.yaml')
bot = Gendo.config_from_yaml(config_path)

#### Helper functions #########################################################

def all_messages(user, channel, message):
    return True


def is_mention(f):
    """Decorator to check if bot is mentioned."""

    def wrapped(user, channel, message):
        BOT_ID_RE = re.compile('<@{}>'.format(bot.id))
        mention = BOT_ID_RE.search(message) is not None
        if mention:
            return f(user, channel, message)

    return wrapped


def message_has_url(user, channel, message):
    return URL_RE.search(message) is not None


def update_channels_list():
    """Update the list of channels from slack."""

    channels_ = bot.client.api_call('channels.list')
    channels = json.loads(channels_.decode('utf8'))['channels']

    for channel in channels:
        id_ = channel['id']
        name = channel['name']
        num_members = channel['num_members']

        channel_obj = session.query(Channel).get(id_)
        if channel_obj is None:
            channel_obj = Channel(id=id_, name=name, num_members=num_members)
            session.add(channel_obj)

        else:
            channel_obj.name = name
            channel_obj.num_members = num_members

    session.commit()


def update_user_list():
    """Update the list of users from slack."""

    users_ = bot.client.api_call('users.list')
    users = json.loads(users_.decode('utf8'))['members']

    for user in users:
        id_ = user['id']
        name = user['name']

        user_obj = session.query(User).get(id_)
        if user_obj is None:
            user_obj = User(id=id_, name=name)
            session.add(user_obj)

        else:
            user_obj.name = name

    session.commit()

#### Bot Functions ############################################################

@bot.listen_for(all_messages)
def logger(user, channel, message):
    message_log = Message(
        user_id=user or 'USLACKBOT',
        channel_id=channel,
        message=message,
        timestamp=datetime.now()
    )
    session.add(message_log)
    session.commit()

@bot.handle_event('channel_created', target_channel='general')
def notify_general(event_data):
    user = event_data['channel']['creator']
    channel = event_data['channel']['id']
    invite_me = (
        "Unfortunately, I can't join the channel automatically. "
        "If you want logging and other fancy features, invite me.\n"
        "/invite @{} {{channel.name}}".format(bot.username)
    )
    response = '{{user.username}} created {{channel.name}}.\n{}'.format(invite_me)
    return user, channel, response

@bot.listen_for('what are you')
@is_mention
def source_code(user, channel, message):
    response = 'Good evening! I am a HAL 9000 computer.'
    return response.format()

@bot.listen_for('explain yourself')
@is_mention
def explain_itself(user, channel, message):
    response = 'The Heuristically programmed ALgorithmic Computer(HAL) 9000 computer is an artificial intelligence and the onboard computer on the spaceship Discovery 1. HAL 9000, more commonly called "Hal", became operational in the HAL plant in Urbana, Illinois, on January 12, 1992. His first instructor was Dr. Chandra. Hal is capable of many functions, such as speech, speech recognition, facial recognition, lip reading, interpreting emotions, expressing emotions, and chess, in addition to maintaining all systems on Discovery.'
    return response.format()



#### Cron functions ###########################################################

@bot.cron('0 0 * * *')
def checkins_reminder():
    date = datetime.now().strftime('%d %B, %Y')
    bot.speak('Morning! What are you doing on {}!'.format(date), "#checkins")


# Run updates on information from slack, every hour.
@bot.cron('* */1 * * *')
def update_info():
    """Update information about slack channels and users."""

    update_channels_list()
    update_user_list()


def main():
    Base.metadata.create_all(engine)
    update_info()
    bot.run()

if __name__ == '__main__':
    main()
