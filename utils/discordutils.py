from core.models import User
import discord

# Ensure that a user exists in the database
# We can't use get_or_create as that will create a new user when username is changed
def ensure_user(user: discord.Member | discord.User | None):
    if user is None:
        raise RuntimeError("Attempting to find nonexistent user")
    if(User.select().where(User.discord_id == user.id).exists()):
        return User.get(User.discord_id == user.id)
    new_user = User(discord_id=user.id, discord_name=user.name, display_name=user.display_name)
    new_user.save()
    return new_user

def check_valid_interaction(interaction: discord.Interaction):
    if not interaction.user:
        raise RuntimeError("Received interaction with no user")
    if not interaction.message:
        raise RuntimeError("Received interaction with no message")
    assert interaction.user is not None
    assert interaction.message is not None
    return interaction

def get_message_url(message: discord.Message) -> str:
    if message.guild is None:
        return ""
    return f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"