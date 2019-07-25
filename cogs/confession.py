from string import ascii_lowercase as ASCII_LOWERCASE
from random import choices, randint

from discord import Embed, DMChannel, Message, PermissionOverwrite
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


    @command()
    @has_permissions(manage_channels=True)
    @bot_has_permissions(manage_channels=True, embed_links=True)
    async def createchannel(self, ctx: Context):
        '''Creates a confession channel for the bot to run responses to'''

        # Get a code that hasn't been cached
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

        # Okay it should be alright - add em to the cache
        self.currently_confessing.add(original_message.author.id)

        # Ask for a channel code
        await channel.send("What's the code for the channel you want to confess to?")
        try:
            code_message = await self.bot.wait_for("message", check=lambda m: isinstance(m.channel, DMChannel) and m.author.id == original_message.author.id, timeout=120)
        except TimeoutError:
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
        confession_channel = self.bot.get_channel(confession_channel_id) or await self.bot.fetch_channel(confession_channel_id)
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

        # Oh boy they are - time to send the confession I guess
        embed = Embed(
            title=f"Confession Code {code.upper()}",
            description=confession,
            timestamp=original_message.created_at,
            colour=randint(1, 0xffffff),
        )
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
        self.log_handler.info(f"Sent confession from {original_message.author.id} to {confession_channel.id} -> {confession}")


def setup(bot:CustomBot):
    x = Confession(bot)
    bot.add_cog(x)
