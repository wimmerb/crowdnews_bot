from datetime import datetime, timedelta
from typing import List
import logging
import string
import random
import json
from collections import defaultdict
from aiogram import Bot, Dispatcher, executor, types
from backend import Phase
import backend
import asyncio
from functools import reduce

#HALLO von AWS

with open("bot_properties.json") as f:
    API_TOKEN = json.load(f)["api_token"]
    
# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
#TODO initialize with the right loop!
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(regexp = "/start")
async def do_start(message: types.Message):
    if backend.get_phase_from_message(message) in [Phase.none]:
        backend.default_state_for_message(message)
        await bot.send_message(message.chat.id, 
                               'Welcome',
                               reply_markup = types.ReplyKeyboardRemove())
    else: 
        await do_help(message)

@dp.message_handler(regexp = "/help")
async def do_help(message: types.Message):
    await bot.send_message(message.chat.id, 
                           'Here\'s some help....',
                           reply_markup = types.ReplyKeyboardRemove())
    backend.default_state_for_message(message)

@dp.message_handler(regexp = "/abort")
async def do_abort(message: types.Message):
    await bot.send_message(message.chat.id, 
                           'Ok. Discarding operation.',
                           reply_markup = types.ReplyKeyboardRemove())
    backend.default_state_for_message(message)


#AnyPhase -> new_group -> new_group_info -> desired_weekday -> desired_hour -> desired_period -> desired_privacy
@dp.message_handler(regexp = "/newgroup")
async def do_create_group(message: types.Message):
    if not backend.get_phase_from_message(message) in [Phase.default]:
        backend.default_state_for_message(message)
    await bot.send_message(message.chat.id, 
                           'Ok! Let\'s create a new group. How do you want to call it?',
                           reply_markup = types.ReplyKeyboardRemove())
    backend.set_phase_for_message(message, Phase.new_group)
    pass


@dp.message_handler(regexp = "/joingroup")
async def do_join_group(message: types.Message):
    if not backend.get_phase_from_message(message) in [Phase.default]:
        backend.default_state_for_message(message)
    #TODO public groups
    await bot.send_message(message.chat.id, 
                           'Please send me an id for the group you want to join or try one of our community\'s public groups!',
                           #backend.get public groups
                           reply_markup = backend.create_keyboard(backend.get_public_group_ids()))
    backend.set_phase_for_message(message, Phase.join_group)
    pass

@dp.message_handler(regexp = "/leavegroup")
async def do_leave_group(message: types.Message):
    if not backend.get_phase_from_message(message) in [Phase.default]:
        backend.default_state_for_message(message)
    await bot.send_message(message.chat.id, 
                           'Which group do you want to leave?',
                           reply_markup = backend.create_keyboard(backend.get_groupids_for_chatid(str(message.chat.id)) + ["/abort"]))
    #TODO phase setzen
    pass

@dp.message_handler(regexp = "/deletegroup")
async def do_delete_group(message: types.Message):
    if not backend.get_phase_from_message(message) in [Phase.default]:
        backend.default_state_for_message(message)
    await bot.send_message(message.chat.id, 
                           'Which group do you want to delete?'
                           #TODO get_administered_groupids_for_chatid
                           )
    #TODO phase setzen
    pass

@dp.message_handler(regexp = "(/add)|(/addcontent)")
async def do_add(message: types.Message):
    if not backend.get_phase_from_message(message) in [Phase.default]:
        backend.default_state_for_message(message)
    await bot.send_message(message.chat.id, 
                           'Please send the message block you want your friends to receive! \nWhen you are done, finish with /done.',
                            reply_markup = backend.create_keyboard(["/done" , "/abort"]))
                           
    backend.set_phase_for_message(message, Phase.add_messages)
    pass

#TODO keine weiteren Nachrichten mit / beginnen lassen
@dp.message_handler(regexp = "/done")
async def do_done(message: types.Message):

    if backend.get_phase_from_message(message) == Phase.add_messages:
        if backend.get_sent_message_ids_from_message(message) != []:
            await bot.send_message(message.chat.id, "Alright. Now let's select the group(s) you want to post this to. \nAfter the selection, finish with /done.", 
                                   reply_markup = backend.create_keyboard(backend.get_groupids_for_chatid(str(message.chat.id)) + ["/done", "/abort"]))
            backend.set_phase_for_message(message, Phase.send_to_groups)
        else:
            await bot.send_message(message.chat.id, 
                                   "A message block must consist of at least one message. \nPlease send some content before you proceed with /done. \nIf you have decided otherwise, you can use /abort.",
                                    reply_markup = backend.create_keyboard(["/done" , "/abort"]))
        return
    elif backend.get_phase_from_message(message) == Phase.send_to_groups:
        if backend.get_receiving_group_ids(message) != []:
            #CHECKEN, ob der Gruppe bereits beigetreten wurde.
            receiving_group_string = reduce(lambda a,b: a+", "+ b, 
                                            backend.get_receiving_group_ids(message))
            await bot.send_message(message.chat.id, 
                                   f"Thanks. Your messages have been stored and will be sent to {receiving_group_string} soon",
                                   reply_markup = types.ReplyKeyboardRemove())
            backend.post_content_to_groups(backend.get_receiving_group_ids(message), 
                                           backend.get_sent_message_ids_from_message(message), 
                                           str(message.chat.id))
            #STOREN!
            backend.default_state_for_message(message)        
        else:
            await bot.send_message(message.chat.id, 
                                   "Please send at least one group ID before you proceed with /done. \nIf you have decided otherwise, you can use /abort.", 
                                   reply_markup = backend.create_keyboard(backend.get_groupids_for_chatid(str(message.chat.id)) + ["/done", "/abort"]))
        return
    else:
        #TODO /done bei Gruppe ohne Name: spezifischer
        await bot.send_message(message.chat.id, 
                               'Hmm. Unfortunately I don\'t understand. /done is used when e.g. posting messages to a group, but not here. \nMaybe you could use some /help?',
                               reply_markup = backend.create_keyboard(["/help"]))
        backend.default_state_for_message(message)
        return
        #todos



@dp.message_handler()
async def do_handle_free_text_message(message: types.Message):
    if backend.get_phase_from_message(message) == Phase.new_group:
        #erwarte gruppenname, dann nächste phase
        #TODO prüfe Message-Type
        await bot.send_message(message.chat.id, 
                               'What a wonderful name for a group! \nPlease send me a message with group info.',
                               reply_markup = backend.create_keyboard(['/abort']))
        backend.set_desired_group_name(message, message.text)
        backend.set_phase_for_message(message, Phase.new_group_info)
        return
    elif backend.get_phase_from_message(message) == Phase.new_group_info:
        #erwarte Textblock, dann nächste Phase
        #TODO prüfe Message-Type
        await bot.send_message(message.chat.id, 
                               'Alright. \nPlease select next on which day of the week the bot shall start posting content.',
                               reply_markup = backend.get_weekday_keyboard())
        backend.set_desired_group_info(message, message.text)
        backend.set_phase_for_message(message, Phase.new_group_desired_weekday)
        return
    elif backend.get_phase_from_message(message) == Phase.new_group_desired_weekday:
        if not backend.is_weekday(message):
            await bot.send_message(message.chat.id, 
                                   f"This is not a proper day of week, please make sure you spell e.g. \'Monday\' with a capital letter.",
                                   reply_markup = backend.get_weekday_keyboard())
            return
        await bot.send_message(message.chat.id,
                               'Great. Please enter the time of day (in Berlin time) when you want me to post to this group',
                               reply_markup = backend.create_keyboard(range(24)))
        backend.set_desired_group_weekday(message, message.text)
        backend.set_phase_for_message(message, Phase.new_group_desired_hour)
        return
    elif backend.get_phase_from_message(message) == Phase.new_group_desired_hour:
        if not backend.is_hour(message):
            await bot.send_message(message.chat.id, 
                                   f"Please send me me a time of day as a number between 0 and 23",
                                    reply_markup = backend.create_keyboard(range(24)))
            return
        await bot.send_message(message.chat.id,
                               'Ok. Please do now select a post frequency as a number in days. 7, for example, would mean weekly postings',
                               reply_markup = backend.create_keyboard(range(1, 8)))
        backend.set_desired_group_hour(message, message.text)
        backend.set_phase_for_message(message, Phase.new_group_desired_period)
        return
    elif backend.get_phase_from_message(message) == Phase.new_group_desired_period:
        #erstelle neue Gruppe
        if not backend.is_proper_period(message):
            await bot.send_message(message.chat.id,
                                   f"Please send me a number between 1 and 365 to determine the post-frequency in this group.",
                                   reply_markup = backend.create_keyboard(range(1, 8)))
            return
        await bot.send_message(message.chat.id,
                               f"Alright. I will post new content to this group every {str(message.text)+' days' if str(message.txt) != 1 else 'daily'}.\nDo you want this group to be private? Private groups will not be suggested to new users of this bot.",
                               reply_markup = backend.create_keyboard(['yes', 'no']))
        backend.set_desired_group_period(message, str(message.text))
        backend.set_phase_for_message(message, Phase.new_group_desired_privacy)
        return
        
    elif backend.get_phase_from_message(message) == Phase.new_group_desired_privacy:
        if not str(message.text) in ['yes', 'no']:
            await bot.send_message(message.chat.id,
                                   f"Please send a yes/no answer.",
                                   reply_markup = backend.create_keyboard(['yes', 'no']))
            return
        group_id = backend.create_group(backend.get_desired_group_name(message), 
                                        backend.get_desired_group_info(message),
                                        backend.get_desired_group_weekday(message),
                                        backend.get_desired_group_hour(message),
                                        backend.get_desired_group_period(message),
                                        message.text, 
                                        str(message.chat.id))
        #TODO group_id kann None sein
        await bot.send_message(message.chat.id, 
                               'The group has been created successfully. \nHere\'s your group ID:')
        await bot.send_message(message.chat.id,  
                               f'{group_id}')
        await bot.send_message(message.chat.id, 
                               'This ID can be used by other people to join your group.',
                               reply_markup = types.ReplyKeyboardRemove())
        backend.default_state_for_message(message)
        return


    elif backend.get_phase_from_message(message) == Phase.add_messages:
        #erwarte Nachrichten, bleib in Phase
        #TODO prüfe Message-Type
        backend.append_sent_message_ids_for_message(message)        
        return
    elif backend.get_phase_from_message(message) == Phase.send_to_groups:
        #erwarte group_ids, bleib in Phase
        #TODO prüfe Message-Type
        backend.append_receving_group_ids(message, message.text)
        return
    elif backend.get_phase_from_message(message) == Phase.join_group:
        #erwarte group_id, dann nächste Phase
        #Versuche, die Gruppe zu joinen
        #TODO prüfe Message-Type
        successful = backend.join_group(message.text, 
                                        str(message.chat.id))
        if successful:
            await bot.send_message(message.chat.id, 
                                   f'Successfully joined {message.text}',
                                   reply_markup = types.ReplyKeyboardRemove())
        else:
            await bot.send_message(message.chat.id, 
                                   f'Something went wrong. Maybe the group {message.text} does not exist or the name was in the wrong format. \nMake sure it looks like this: abcd#1234',
                                   reply_markup = types.ReplyKeyboardRemove())
        backend.default_state_for_message(message)
        return
    #TODO: handle ALL Phases including default
    else:
        await bot.send_message(message.chat.id, 
                               'I do not understand what you are saying. \nTry typing /help for some instructions.',
                               reply_markup = types.ReplyKeyboardRemove())
        backend.default_state_for_message(message)


async def post_messages():
    #TODO: RIGHT TIMES, ADD PERIOD TO DATASTRUCTURE
    #TODO: make own Bot with proper name
    #TODO: get on github
    while True:
        for group_id in backend.get_due_groups():
            to_post = backend.pop_message_from_group(group_id)
            if to_post is None:
                for rcv_id in backend.get_chatids_for_groupid(group_id):
                    await bot.send_message(rcv_id, 
                                           f"😕\nUnfortunately, your group {group_id} is out of new messages... \nUse /add to post some new content to this group",
                                           reply_markup = backend.create_keyboard(["/add"]))
                    await asyncio.sleep(0.5)
            else:
                from_chat_id, message_ids = to_post
                for rcv_id in backend.get_chatids_for_groupid(group_id):
                    
                    for message_id in message_ids:
                        await bot.send_message(rcv_id, 
                                               f"📫\nHere's today's content from {group_id}",
                                               reply_markup = types.ReplyKeyboardRemove())
                        await bot.forward_message(rcv_id, 
                                                  from_chat_id, 
                                                  message_id)
                        await asyncio.sleep(0.5)
        await asyncio.sleep(20)
    


if __name__ == '__main__':
    try:
        dp.loop.create_task(post_messages())
        executor.start_polling(dp, skip_updates=True)
        #Starte mit Loop...
        #asyncio.create_task(loop.run_in_executor(exec, funny_aio))
    finally:
        #to_string()
        backend.dump_string()
