from peewee import (AutoField,
                    CharField, IntegerField, TimestampField, BooleanField, DateTimeField,
                    ForeignKeyField, Model, TextField, SqliteDatabase, TimeField)
import datetime
from enum import IntEnum, auto

class AntiSpamResolveAction(IntEnum):
    UNMUTE = auto()
    DELETE_MESSAGES = auto()
    DELETE_AND_KICK = auto()

database = SqliteDatabase(None)

class ModelBase(Model):
    class Meta:
        database = database

class User(ModelBase):
    user_id = AutoField()
    discord_id = CharField(max_length=20)
    discord_name = CharField(max_length=128)
    display_name = CharField(max_length=128)

class WDApplication(ModelBase):
    application_id = AutoField()
    user_id = IntegerField()
    username = CharField(max_length=128)
    unix_name = CharField(max_length=128)
    text = TextField()
    submitted = TimestampField(default=datetime.datetime.now)
    resolved = BooleanField(default=False)
    resolved_at = TimestampField(null=True, default=None)
    resolved_by = ForeignKeyField(User, backref='applications', null=True)
    resolved_externally = BooleanField(default=False)
    accepted = BooleanField(null=True)

class LostCycle(ModelBase):
    id = AutoField()
    started = DateTimeField(default=datetime.datetime.now)
    ended = DateTimeField(null=True)
    
class LostCycleReset(ModelBase):
    id = AutoField()
    timestamp = DateTimeField(default=datetime.datetime.now)
    cycle = ForeignKeyField(LostCycle, backref='resets')
    user = ForeignKeyField(User, backref='resets')

class AntispamTriggerEvent(ModelBase):
    id = AutoField()
    event_timestamp = DateTimeField(default=datetime.datetime.now)
    resolution_timestamp = DateTimeField(null=True, default=None)
    offending_user = ForeignKeyField(User, backref='mutes')
    resolving_user = ForeignKeyField(User, backref='resolved_incidents', null=True, default=None)
    moderator_action = IntegerField(null=True)
    muted_for = TimeField()
    message_content = TextField()
    attachment_count = IntegerField()
    
class SpamAttachmentHash(ModelBase):
    id = AutoField()
    hexdigest = CharField(32) # We use BLAKE2b-128, which means 16 byte digest - 32 hex chars
    filename = TextField()
    event = ForeignKeyField(AntispamTriggerEvent, backref='attachments')

class StarboardPinnedMessage(ModelBase):
    id = AutoField()
    message_id = CharField(15) # 15 chars should be enough for the forseeable future
    emoji = CharField(64)
    pinned_at = TimestampField(null=True, default=None)
    reaction_count = IntegerField(default=0)
    created_at = TimestampField(default=datetime.datetime.now)