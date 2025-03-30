from models import User
import discord

# Ensure that a user exists in the database
# We can't use get_or_create as that will create a new user when username is changed
def ensure_user(user: discord.Member | discord.User):
    if(User.select().where(User.discord_id == user.id).exists()):
        return User.get(User.discord_id == user.id)
    new_user = User(discord_id=user.id, discord_name=user.name, display_name=user.display_name)
    new_user.save()
    return new_user