from telegram.ext import Filters, CommandHandler, MessageHandler, ConversationHandler
from bot import commands
from bot.convos import config_chat, edit

convo_text_filter = Filters.text & ~Filters.command

edit_handler = ConversationHandler(
    entry_points=[CommandHandler("edit", commands.edit_job)],
    states={
        edit.state0: [MessageHandler(convo_text_filter, edit.choose_job)],
        edit.state1: [MessageHandler(convo_text_filter, edit.choose_attribute)],
        edit.state2: [
            MessageHandler(convo_text_filter, edit.handle_edit_content),
            MessageHandler(Filters.poll, edit.handle_edit_poll),
        ],
        edit.state3: [MessageHandler(Filters.photo, edit.handle_add_photo)],
        edit.state4: [MessageHandler(convo_text_filter, edit.handle_clear_photos)],
    },
    fallbacks=[MessageHandler(Filters.command, edit.end_convo)],
)


config_chat_handler = ConversationHandler(
    entry_points=[CommandHandler("changesender", commands.change_sender)],
    states={
        config_chat.state0: [
            MessageHandler(convo_text_filter, config_chat.choose_chat)
        ],
        config_chat.state1: [
            MessageHandler(convo_text_filter, config_chat.update_sender)
        ],
    },
    fallbacks=[MessageHandler(Filters.command, edit.end_convo)],
)
