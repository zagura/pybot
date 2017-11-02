import json
import os
import sqlite3

from datetime import datetime
from threading import Lock
from plugin import *


class note(plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.db_name = self.bot.config['server']
        os.makedirs(os.path.dirname(os.path.realpath(self.config['db_location'])), exist_ok=True)
        self.db_connection = sqlite3.connect(self.config['db_location'], check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()
        self.db_cursor.execute(f"CREATE TABLE IF NOT EXISTS '{self.db_name}' (nickname TEXT primary key not null, notes TEXT)")  # nickname -> [msgs, to, send]
        self.db_mutex = Lock()

    def on_pubmsg(self, source, **kwargs):
        notes = self.get_notes_for_user(source.nick)
        if not notes: return

        self.bot.say(f'{source.nick}, you have notes!')
        for _note in notes: self.bot.say(_note)

        with self.db_mutex:
            self.db_cursor.execute(f"DELETE FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (source.nick,))
            self.db_connection.commit()

        self.logger.info(f'notes given to {source.nick}')

    @command
    @doc('note <nickname> <message>: store <message> for <nickname>')
    def note(self, sender_nick, msg, **kwargs):
        if not msg: return
        target = msg.split()[0]
        if target == self.bot.get_nickname():
            self.bot.say("you won't trick me")
            return
        
        new_note = msg[len(target):].strip()
        self.logger.info(f'{sender_nick} notes "{new_note}" for {target}')
        if not new_note: return
        new_note = f'{datetime.now().strftime("%d-%m-%Y %H:%M")}  <{sender_nick}> {new_note}'

        saved_notes = self.get_notes_for_user(target)

        if saved_notes:
            saved_notes.extend([new_note])
            with self.db_mutex:
                self.db_cursor.execute(f"UPDATE '{self.db_name}' SET notes = ? WHERE nickname = ?", (json.dumps(saved_notes), target.casefold()))
                self.db_connection.commit()
        else:
            with self.db_mutex:
                self.db_cursor.execute(f"INSERT INTO '{self.db_name}' VALUES (?, ?)", (target.casefold(), json.dumps([new_note])))
                self.db_connection.commit()

        self.bot.say_ok()

    def get_notes_for_user(self, nickname):
        with self.db_mutex:
            self.db_cursor.execute(f"SELECT notes FROM '{self.db_name}' WHERE nickname = ? COLLATE NOCASE", (nickname,))
            result = self.db_cursor.fetchone()

        if result:
            result = list(json.loads(result[0]))

        return result
