from peewee import *
import datetime

database = SqliteDatabase(None)

class ModelBase(Model):
    class Meta:
        database = database

class User(ModelBase):
    user_id = AutoField()
    discord_id = CharField(max_length='20')
    discord_name = CharField(max_length='128')
    display_name = CharField(max_length='128')

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