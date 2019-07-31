from string import ascii_lowercase as ASCII_LOWERCASE
from random import choices, randint
from asyncio import TimeoutError as AsyncTimeoutError
from typing import Dict
from datetime import datetime as dt

from asyncpg import UniqueViolationError
from discord import Embed, DMChannel, Message, PermissionOverwrite, User
from discord.errors import NotFound as DiscordNotFound
from discord.ext.commands import command, has_permissions, bot_has_permissions, Context, MissingPermissions, BotMissingPermissions

from cogs.utils.custom_bot import CustomBot
from cogs.utils.custom_cog import Cog


CODEDIGITS = ASCII_LOWERCASE + '0123456789'
def get_code(n:int=5) -> str:
    return ''.join(choices(CODEDIGITS, k=n))


class Confession(Cog):

    def __init__(self, bot: CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot
        self.currently_confessing = set()  # A set rather than a list because it uses a hash table
        self.confession_users: Dict[str, User] = {}  # uuid: User


    async def cog_error(self, ctx:Context, error):
        '''Handles errors for this particular cog'''

        if isinstance(error, MissingPermissions):
            error: MissingPermissions = error
            if ctx.author.id in self.bot.config['owners']:
                await ctx.reinvoke() 
                return 
            await ctx.send(f"You need to have the `{error.missing_perms[0]}` permission to run this command.")
    
        elif isinstance(error, BotMissingPermissions):
            await ctx.send(f"I'm missing the `{error.missing_perms[0]} permission required to run this command.")

        raise error


    @command()
    @has_permissions(manage_messages=True)
    async def banuser(self, ctx:Context, uuid:str):
        '''Bans a user from being able to send in any more confessions to your server'''

        # Make sure it's valid
        if len(uuid) != 16:
            await ctx.send("You've not posted a valid ID. Please try again.")
            return 

        # Make sure it's real
        if uuid.lower() not in self.confession_users:
            await ctx.send("The ID provided is not one that I currently have cached. Please try again.")
            return 

        # Get and ban em
        user_to_ban = self.confession_users.get(uuid.lower())
        if user_to_ban is None:
            await ctx.send("The ID provided doesn't point to a user. Please try again.")
        async with self.bot.database() as db:
            try:
                await db('INSER INTO banned_users (guild_id, user_id) VALUES ($1, $2)', ctx.guild.id, user_to_ban.id)
            except UniqueViolationError:
                pass 

        # Tell people about it
        try:
            await user_to_ban.send("You've been banned from posting confessions on the server **{ctx.guild.id}**. Your identity is still a secret. Don't worry about it too much.")
        except Exception:
            pass
        await ctx.send("That user has been banned from sending in more confessions on your server.")



    @command()
    @has_permissions(manage_channels=True)
    @bot_has_permissions(manage_channels=True)
    async def createchannel(self, ctx: Context, code:str=None):
        '''Creates a confession channel for the bot to run responses to'''

        # Get a code for the user
        if code:
            if len(code) > 5:
                await ctx.send("The maximum length for your channel code is 5 characters.")
                return 
            if code.lower() in self.bot.confession_channels:
                await ctx.send(f"The code `{code}` is already in use. Sorry :/")
                return
            code = code.lower()
        else:
            while True:
                code = get_code()
                if code not in self.bot.confession_channels:
                    break

        # Create a channel with that name
        overwrites = {
            ctx.guild.default_role: PermissionOverwrite(read_messages=True, send_messages=False),
            ctx.guild.me: PermissionOverwrite(send_messages=True, embed_links=True),
        }
        channel = await ctx.guild.create_text_channel(
            f"confessional-{code}",
            reason="Confessional channel created",
            topic=f"A confessional channel for use with {ctx.guild.me.mention}. The code for this channel is \"{code.upper()}\". PM the bot your confession, and then provide \"{code.upper()}\" as your channel code when it's asked for.",
            overwrites=overwrites,
        )

        # Cache it
        self.bot.confession_channels[code] = channel.id

        # DB it
        async with self.bot.database() as db:
            await db('INSERT INTO confession_channel VALUES ($1, $2)', code, channel.id)

        # Tell em it's done
        await ctx.send(f"Your new confessional channel has been created over at {channel.mention}")

    
    @Cog.listener('on_message')
    async def confession_listener(self, message: Message):
        '''Listens out for a message in a DM channel and assumes it's a confession'''

        # Handle guild channels
        if not isinstance(message.channel, DMChannel):
            return
        
        # Handle bots (me lol)
        if message.author.bot:
            return

        # Handle them giving a code
        if message.author.id in self.currently_confessing:
            return

        # Set up this name error lol
        channel = message.channel 
        original_message = message

        # Assume they're just sending a message - whereabouts do they want to send it
        confession = original_message.content
        if len(confession) > 1000:
            await channel.send("Your confession can only be 1000 characters I'm afraid - please shorten it and try again.")
            return
        elif original_message.attachments:
            await channel.send("I don't support sending images right now, I'm afraid. Sorry!")
            return

        # Okay it should be alright - add em to the cache
        self.currently_confessing.add(original_message.author.id)

        # Ask for a channel code
        await channel.send("What's the code for the channel you want to confess to?")
        try:
            code_message = await self.bot.wait_for("message", check=lambda m: isinstance(m.channel, DMChannel) and m.author.id == original_message.author.id, timeout=120)
        except AsyncTimeoutError:
            await channel.send("The timer for you to give a channel code has timed out. Please give your confession again to be able to provide another.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return

        # Check their channel code is real
        if len(code_message.content) != 5 or self.bot.confession_channels.get(code_message.content.lower()) is None:
            await channel.send(f"The code `{code_message.content}` doesn't refer to a given confession channel. Please give your confession again to be able to provide a new channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return
        code = code_message.content.lower()

        # Check the bot can get the channel
        confession_channel_id = self.bot.confession_channels.get(code)
        if confession_channel_id is None:
            await channel.send(f"The code `{code_message.content}` doesn't refer to a given confession channel. Please give your confession again to be able to provide a new channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return
        try:
            confession_channel = self.bot.get_channel(confession_channel_id) or await self.bot.fetch_channel(confession_channel_id)
        except DiscordNotFound:
            confession_channel = None
        if confession_channel is None:
            await channel.send(f"The code `{code_message.content}` doesn't refer to a given confession channel. Please give your confession again to be able to provide a new channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return

        # Check the user is in the guild for the channel
        if original_message.author.id not in confession_channel.guild._members:
            await channel.send(f"You're not in the guild that the channel code `{code}` refers to. Please give your confession again and provide an alternative channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return

        # Check they're allowed to send messages to that guild
        if (confession_channel.guild.id, original_message.author.id) in self.bot.banned_users:
            await channel.send("You've been banned from sending messages in to that server :/")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return

        # Oh boy they are - time to send the confession I guess
        embed = Embed(
            title=f"Confession Code {code.upper()}",
            description=confession,
            timestamp=dt.utcnow(),
            colour=randint(1, 0xffffff),
        )
        user_ban_code = get_code(16)
        self.confession_users[user_ban_code] = original_message.author
        embed.set_footer(text=f",banuser {user_ban_code}")
        try:
            confessed_message = await confession_channel.send(embed=embed)
        except Exception as e:
            await channel.send(f"I encoutered the error {e} trying to send in the confession :/")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass 
            return
        await channel.send(f"I sucessfully sent in your confession!\n{confessed_message.jump_url}")
        try:
            self.currently_confessing.remove(original_message.author.id)
        except KeyError:
            pass 
        self.log_handler.info(f"Sent confession from {original_message.author.id} to {confession_channel.id} ({code: >5}) -> {confession}")

        # Log it to db
        async with self.bot.database() as db:
            await db(
                'INSERT INTO confession_log (confession_message_id, user_id, guild_id, channel_code, channel_id, timestamp, confession) VALUES ($1, $2, $3, $4, 45, $6, $7)',
                confessed_message.id, 
                original_message.author.id,
                confession_channel.guild.id,
                code.lower(),
                confession_channel.id,
                confessed_message.created_at,
                confession,
            )


def setup(bot:CustomBot):
    x = Confession(bot)
    bot.add_cog(x)
