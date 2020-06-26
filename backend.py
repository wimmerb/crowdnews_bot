from datetime import datetime, timedelta
from typing import List, Tuple, Union
import logging
import string
import random
import json
import math
from collections import defaultdict
from aiogram import types
from JSON_helper import setify, listify

now = lambda: datetime.now().utcnow() + timedelta(hours = 2)

with open("groupmatrix.json") as f:
    group_matrix = json.load(f)
    groupid_to_chatids = defaultdict(set, setify(group_matrix.setdefault('groupid_to_chatids', dict())))
    chatid_to_groupids = defaultdict(set, setify(group_matrix.setdefault('chatid_to_groupids', dict())))
    groupid_to_group = defaultdict(dict, group_matrix.setdefault('groupid_to_group', dict()))
    #posted_messages MUST be initialized as defaultdict, maybe even the same with the dates one layer deeper
    #maybe do everything with usual dicts first, then change into defaultdict recursively
    for group in groupid_to_group.values():
        group['posted_messages'] = defaultdict(lambda: defaultdict(list), group.setdefault('posted_messages', defaultdict(list)))

    
with open ("chat_states.json") as f:
    chat_states = json.load(f)
    chat_states = defaultdict(dict, chat_states)


#------------------------------------------------data management----------------------------------------------------#
def create_group(group_name: str, 
                 group_info: str, 
                 desired_weekday: str, 
                 desired_hour: str,
                 desired_period: str,
                 desired_privacy: str,
                 admin_chatid: str):
    def create_groupid():
        #Todo check for loophole
        id = str(random.randrange(0, 1000, 1)).zfill(4)
        return create_groupid() if groupid_to_group.get(id, None) != None else id
    group_id = f"{group_name}#{create_groupid()}"
    groupid_to_group[group_id] = {  'admin_id': admin_chatid, 
                                    'group_id': group_id, 
                                    'group_name': group_name,
                                    'group_info': group_info,
                                    'update_period': desired_period,
                                    'update_due': create_initial_date(desired_weekday, 
                                                                      desired_hour),
                                    'is_private' : desired_privacy,
                                    'posted_messages': defaultdict(lambda: defaultdict(list))
                                    }
    chatid_to_groupids[admin_chatid].add(group_id)
    groupid_to_chatids[group_id].add(admin_chatid)
    return group_id

def join_group(group_id: string, chat_id: string):
    #check existence before...
    if group_id in groupid_to_group:
        chatid_to_groupids[chat_id].add(group_id)
        groupid_to_chatids[group_id].add(chat_id)
        return True
    return False
    
def leave_group(group_id: string, chat_id: string):
    #what to check before?
    #TODO remove entries in groupid_to_group
    if chat_id in chatid_to_groupids and group_id in groupid_to_chatids:
        chatid_to_groupids[chat_id].discard(group_id)
        groupid_to_chatids[group_id].discard(chat_id)
        if not groupid_to_chatids[group_id]:
            delete_group(group_id)
        return True
    return False
    #what to check after?

def delete_group(group_id: string):
    #what to check before
    #TODO CHECK functionality
    groupid_to_chatids.pop(group_id, None)
    groupid_to_group.pop(group_id, None)
    for _, value in chatid_to_groupids.items():
        value.discard(group_id)
    return True

def post_content_to_groups(group_ids: List[str], message_ids: List[str], chat_id: str):
    for group_id in group_ids:
        #ensure that there will not be posted to non-existent groups
        if group_id in groupid_to_group.keys(): 
            groupid_to_group[group_id]['posted_messages'][chat_id][str(now())] = message_ids
    dump_string()
    return

weekdays = {'Monday': 0, 
            'Tuesday': 1, 
            'Wednesday': 2, 
            'Thursday': 3, 
            'Friday': 4, 
            'Saturday': 5, 
            'Sunday': 6}

def create_initial_date(weekday: str, hour: Union[str, int]) -> str:
    onDay = lambda date, day: date + timedelta(days=(day-date.weekday()+7)%7)
    ret = onDay(now(), weekdays.get(weekday, 0))
    ret = ret.replace(microsecond=0, second=0, minute=0, hour = int(hour))
    ret = ret + timedelta(days = 7) if now() > ret else ret
    return str(ret)

def to_string():
    print(groupid_to_chatids)
    print(groupid_to_group)
    print(chatid_to_groupids)
    return

def dump_string():
    with open('groupmatrix.json', 'w') as handle:
            group_matrix['groupid_to_chatids'] = listify(groupid_to_chatids)
            group_matrix['chatid_to_groupids'] = listify(chatid_to_groupids)
            group_matrix['groupid_to_group'] = groupid_to_group
            json.dump(group_matrix, handle, indent = 4)
    with open ('chat_states.json', 'w') as handle:
        json.dump(chat_states, handle, indent = 4)
    return
#------------------------------------------------data management----------------------------------------------------#


#------------------------------------------------controller for chat------------------------------------------------#
class Phase():
    none = ''
    default = 'default'
    join_group = 'join_group'
    new_group = 'new_group'
    new_group_info = 'new_group_info'
    new_group_desired_weekday = 'new_group_desired_day'
    new_group_desired_hour = 'new_group_desired_hour'
    new_group_desired_period = 'new_group_desired_period'
    new_group_desired_privacy = 'new_group_desired_privacy'
    add_messages = 'add_messages'
    send_to_groups = 'send_to_groups'
    delete_group = 'delete_group'
    leave_group = 'leave_group'

    #TODO GETTER NUR COPIES
def get_chatids_for_groupid(group_id: str):
    return list(groupid_to_chatids[group_id].copy())

def get_groupids_for_chatid(chat_id: str):
    return list(chatid_to_groupids[chat_id].copy())

#TODO get_administered_groupids_for_chatid

def get_phase_from_message(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('phase', Phase.none)

def set_phase_for_message(message: types.Message, state: string):
    chat_states[str(message.chat.id)]['phase'] = state
    dump_string()
    return

def get_sent_message_ids_from_message(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('message_ids', [])

def append_sent_message_ids_for_message(message: types.Message):
    chat_states[str(message.chat.id)].setdefault('message_ids', []).append(str(message.message_id))
    dump_string()
    return

def get_receiving_group_ids(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('receiving_group_ids', [])

def append_receving_group_ids(message: types.Message, group_id: string):
    chat_states[str(message.chat.id)].setdefault('receiving_group_ids', []).append(str(group_id))
    dump_string()
    return

def set_desired_group_name(message: types.Message, desired_group_name: str):
    chat_states[str(message.chat.id)]['desired_group_name'] = desired_group_name
    dump_string()
    return

def get_desired_group_name(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('desired_group_name', None)

def set_desired_group_info(message: types.Message, desired_group_info: str):
    chat_states[str(message.chat.id)]['desired_group_info'] = desired_group_info
    dump_string()
    return

def get_desired_group_info(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('desired_group_info', None)

def set_desired_group_weekday(message: types.Message, desired_group_weekday: str):
    chat_states[str(message.chat.id)]['desired_group_weekday'] = desired_group_weekday
    dump_string()
    return

def get_desired_group_weekday(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('desired_group_weekday', None)

def set_desired_group_hour(message: types.Message, desired_group_hour: str):
    chat_states[str(message.chat.id)]['desired_group_hour'] = desired_group_hour
    dump_string()
    return

def get_desired_group_hour(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('desired_group_hour', None)

def set_desired_group_period(message: types.Message, desired_group_period: str):
    chat_states[str(message.chat.id)]['desired_group_period'] = desired_group_period
    dump_string()
    return

def get_desired_group_period(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('desired_group_period', None)

def get_targeted_group(message: types.Message):
    return chat_states[str(message.chat.id)].setdefault('targeted_group', None)

def set_targeted_group(message: types.Message, targeted_group: string):
    chat_sates[str(message.chat.id)]['targeted_group'] = targeted_group
    dump_string()
    return

def get_public_group_ids():
    return [group_id for group_id, info in groupid_to_group.items() 
            if info['is_private'] == 'no']



def default_state_for_message(message: types.Message):
    chat_states[str(message.chat.id)]['message_ids'] = []
    chat_states[str(message.chat.id)]['receiving_group_ids'] = []
    chat_states[str(message.chat.id)]['desired_group_name'] = None
    chat_states[str(message.chat.id)]['desired_group_info'] = None
    chat_states[str(message.chat.id)]['desired_group_weekday'] = None
    chat_states[str(message.chat.id)]['desired_group_hour'] = None
    chat_states[str(message.chat.id)]['desired_group_period'] = None
    chat_states[str(message.chat.id)]['targeted_group'] = None
    chat_states[str(message.chat.id)]['phase'] = Phase.default
    
    dump_string()
    return

def get_due_groups() -> List[str]:
    #update due date...
    ret = [group_id for group_id, group in groupid_to_group.items() if datetime.strptime(group['update_due'],  '%Y-%m-%d %H:%M:%S') <= now()]
    update_due_groups(ret)
    return ret

def update_due_groups(group_ids: List[str]):
    for group_id in group_ids:
        group = groupid_to_group[group_id]
        group['update_due'] = (str(datetime.strptime(group['update_due'],  '%Y-%m-%d %H:%M:%S')
                                  + timedelta(days = int(group['update_period']))))
        dump_string()
    return


def pop_message_from_group(group_id: string) -> Tuple[str, List[str]]:
    #TODO test
    posted_messages = groupid_to_group[group_id]["posted_messages"]

    #only needed, when not sure if there are no empty entries
    available_posters = []
    for id, entry in posted_messages.items():
        if entry:
            available_posters.append(id)
    if not available_posters:
        return None
    chat_id = random.choice(available_posters)
    key = random.choice(list(posted_messages[chat_id].keys()))
    ret = (chat_id, posted_messages[chat_id].pop(key, None))
    dump_string()
    return ret


def create_keyboard(messages: List):
    def resize(x):
        if not len(x) > 0:
            return [[]]
        l = x[0]
        nr = len(l)
        if nr % 2 == 0 and nr % 3 != 0:
            return reshape(l, 2)
        else:
            return reshape(l, 3)

    def reshape(l, size):
        ret = [[] for x in range(math.ceil(len(l)/size))]
        for i in range(len(l)):
            ret[math.floor(i/size)].append(l[i])
        return ret

    #TODO: formatieren a-la Destinator
    return types.ReplyKeyboardMarkup(keyboard = resize([[types.KeyboardButton(text = x) for x in messages]]))

def get_weekday_keyboard():
    return create_keyboard(weekdays.keys())
#------------------------------------------------controller for chat------------------------------------------------#

#------------------------------------------------controller for times-----------------------------------------------#
def is_weekday(message: types.Message):
    #assumption: Textmessage
    return message.text in weekdays.keys()

def is_hour(message: types.Message):
    #assumption: Textmessage
    if not message.text.isnumeric():
        return False
    if not 0 <= int(message.text) <= 23:
        return False
    return True

def is_proper_period(message: types.Message):
    if not message.text.isnumeric():
        return False
    if not 1 <= int(message.text) <= 365:
        return False
    return True
#------------------------------------------------controller for times-----------------------------------------------#
