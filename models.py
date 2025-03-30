from peewee import *
import datetime

database = SqliteDatabase(None)

class User(Model):
    user_id = AutoField()
    discord_id = CharField(max_length='20')
    discord_name = CharField(max_length='128')
    display_name = CharField(max_length='128')

    class Meta:
        database = database

class WDApplication(Model):
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

    class Meta:
        database = database

class LostCycle(Model):
    id = AutoField()
    started = DateTimeField()
    ended = DateTimeField(null=True)
    
class LostCycleReset(Model):
    id = AutoField()
    timestamp = DateTimeField()
    cycle = ForeignKeyField(LostCycle, backref='resets')
    user = ForeignKeyField(User, backref='resets')