import string
import random
import asyncio
import typing
from datetime import datetime as dt

import asyncpg
import discord
from discord.ext import commands

from cogs import utils


def get_code(n:int=5) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


class Confession(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot
        self.currently_confessing = set()  # A set rather than a list because it uses a hash table
        self.confession_users: typing.Dict[str, discord.User] = {}  # uuid: User

    async def cog_command_error(self, ctx:commands.Context, error):
        '''Handles errors for this particular cog'''

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I'm missing the `{error.missing_perms[0]}` permission that's required for me to run this command.")
            return

<<<<<<< Updated upstream
        elif isinstance(error, commands.MissingPermissions):
            if ctx.author.id in self.bot.config['owners']:
                await ctx.reinvoke()
                return
            await ctx.send(f"You need to have the `{error.missing_perms[0]}` permission to run this command.")

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing the `{error.param.name}` argument, which is required to run this command.")
            return

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"You're running this command incorrectly - {error}")
            return

        raise error

    @commands.command()
=======
    @commands.command(name="banuser",
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    required=True,
                    name="uuid",
                    type=discord.ApplicationCommandOptionType.string,
                    description="User's UUID",
                )
            ]
        ))
>>>>>>> Stashed changes
    @commands.has_permissions(manage_messages=True)
    async def banuser(self, ctx:commands.Context, uuid:str):
        '''Bans a user from being able to send in any more confessions to your server'''

        try:
            user_to_ban = await commands.MemberConverter().convert(ctx, uuid)
        except commands.BadArgument:
            user_to_ban = None

        # Make sure it's valid
        if user_to_ban is None and len(uuid) != 16:
            await ctx.send("You've not posted a valid ID - please give a ban code from a confession.")
            return

        # Make sure it's real
        if user_to_ban is None and uuid.lower() not in self.confession_users:
            await ctx.send("The ID provided is not one that I currently have cached. Please try again.")
            return

        # Get and ban em
        if user_to_ban is None:
            user_to_ban = self.confession_users.get(uuid.lower())
        if user_to_ban is None:
            await ctx.send("The ID provided doesn't point to a user. Please try again.")
            return
        async with self.bot.database() as db:
            try:
                await db('INSERT INTO banned_users (guild_id, user_id) VALUES ($1, $2)', ctx.guild.id, user_to_ban.id)
            except asyncpg.UniqueViolationError:
                pass

        # Tell people about it
        try:
            await user_to_ban.send("You've been banned from posting confessions on the server **{ctx.guild.id}**. Your identity is still a secret. Don't worry about it too much.")
        except Exception:
            pass
        self.bot.banned_users.add((ctx.guild.id, user_to_ban.id))
        await ctx.send("That user has been banned from sending in more confessions on your server.")

<<<<<<< Updated upstream
    @commands.command()
=======
    @commands.command(name="unbanuser",
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    required=True,
                    name="user_id",
                    type=discord.ApplicationCommandOptionType.user,
                    description="User's Discord ID",
                )
            ]
        ))
>>>>>>> Stashed changes
    @commands.has_permissions(manage_messages=True)
    async def unbanuser(self, ctx:commands.Context, user:discord.User):
        '''Unbans a user from messaging the confessional on your server'''

        try:
            self.bot.banned_users.remove((ctx.guild.id, user.id))
        except Exception:
            pass
        async with self.bot.database() as db:
            await db('DELETE FROM banned_users WHERE guild_id=$1 AND user_id=$2', ctx.guild.id, user.id)
        await ctx.send("That user has been unbanned from sending in messages, if they were even banned at all.")

<<<<<<< Updated upstream
    @commands.command()
=======
    @commands.command(name="createchannel",
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    required=False,
                    name="code",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Channel confessional code",
                )
            ]
        ))
>>>>>>> Stashed changes
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def createchannel(self, ctx:commands.Context, code:str=None):
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
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True),
        }
        channel = await ctx.guild.create_text_channel(
            f"confessional-{code}",
            reason="Confessional channel created",
            topic=f"A confessional channel for use with {ctx.guild.me.mention}. The code for this channel is \"{code.upper()}\". PM the bot your confession, and then provide \"{code.upper()}\" as your channel code when it's asked for.",
            overwrites=overwrites,
        )

        # Cache it
        self.bot.confession_channels[code] = channel.id

<<<<<<< Updated upstream
        # DB it
        async with self.bot.database() as db:
            await db('INSERT INTO confession_channel VALUES ($1, $2)', code, channel.id)

        # Tell em it's done
        await ctx.send(f"Your new confessional channel has been created over at {channel.mention}")
=======
    @commands.command(name="setchannel",
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    required=False,
                    name="channel",
                    type=discord.ApplicationCommandOptionType.channel,
                    description="Channel to send confessions",
                ),
                discord.ApplicationCommandOption(
                    required=False,
                    name="code",
                    type=discord.ApplicationCommandOptionType.string,
                    description="Channel confessional code",
                )
            ]
        ))
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.guild_only()
    async def setchannel(self, ctx: vbu.Context, channel: discord.TextChannel = None, code: str = None):
        """
        Sets a confession channel for the bot to run responses to.
        """

        # Get a code for the user
        if code:
            if len(code) > 5:
                return await ctx.send("The maximum length for your channel code is 5 characters.")
            code = code.lower()


        # Check their code is valid, or provide a new one
        async with self.bot.database() as db:
            if code:
                if await db("SELECT * FROM confession_channel WHERE code=$1", code):
                    return await ctx.send(f"The code **{code.upper()}** is already in use.")
            else:
                while True:
                    code = get_code()
                    if not await db("SELECT * FROM confession_channel WHERE code=$1", code):
                        break

        # Check if channel is specificed
        if channel==None:
            channel=ctx.channel

        # See if we can send messages there
        me = await ctx.guild.fetch_member(self.bot.user.id)
        if not channel.permissions_for(me).send_messages:
            return await ctx.send("I don't have permission to send messages into that channel! Please fix this and try running the command again.")

        # And done
        async with self.bot.database() as db:
            await db("INSERT INTO confession_channel VALUES ($1, $2)", code, channel.id)
        await ctx.send(f"Your new confessional channel has been set in {channel.mention}! Just DM me your confession, give the channel code **{code.upper()}**, and that'll be that!")

    @commands.command(name="confess",
        application_command_meta=commands.ApplicationCommandMeta(
            options=[
                discord.ApplicationCommandOption(
                    required=True,
                    name="confession_channel",
                    type=discord.ApplicationCommandOptionType.channel,
                    description="Channel to send confessions",
                ),
                discord.ApplicationCommandOption(
                    required=True,
                    name="confession",
                    type=discord.ApplicationCommandOptionType.string,
                    description="confession to send",
                )
            ]
        ))
    async def confess(self, ctx: vbu.Context, confession_channel: discord.TextChannel, *, confession: str):
        """
        Send a message over to a confession channel.
        """

        await self.send_confession(
            response_channel=ctx,
            author=ctx.author,
            confession=confession,
            confession_code=confession_channel,
        )
>>>>>>> Stashed changes

    @utils.Cog.listener('on_message')
    async def confession_listener(self, message: discord.Message):
        '''Listens out for a message in a DM channel and assumes it's a confession'''

        # Handle guild channels
        if not isinstance(message.channel, discord.DMChannel):
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
<<<<<<< Updated upstream
            await channel.send("Your confession can only be 1000 characters I'm afraid - please shorten it and try again.")
            return
        elif original_message.attachments:
            await channel.send("I don't support sending images right now, I'm afraid. Sorry!")
            return
=======
            return await message.channel.send(
                "Your confession can only be 1000 characters - please shorten it and try again.",
            )
        elif message.attachments:
            return await message.channel.send(
                "I don't support sending images right now.",
            )
>>>>>>> Stashed changes

        # Okay it should be alright - add em to the cache
        self.currently_confessing.add(original_message.author.id)

        # Ask for a channel code
        await channel.send("What's the code for the channel you want to confess to?")
        try:
            code_message = await self.bot.wait_for("message", check=lambda m: isinstance(m.channel, discord.DMChannel) and m.author.id == original_message.author.id, timeout=120)
        except asyncio.TimeoutError:
            await channel.send("The timer for you to give a channel code has timed out. Please give your confession again to be able to provide another.")
            try:
<<<<<<< Updated upstream
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
=======
                await message.channel.send(
                    "The timer for you to give a channel code has timed out. Please give your confession again to be able to provide another.",
                )
            except Exception:
>>>>>>> Stashed changes
                pass
            return

        # Check their channel code is real
        if self.bot.confession_channels.get(code_message.content.lower()) is None:
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
<<<<<<< Updated upstream
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
=======
                if isinstance(confession_code, str):
                    await response_channel.send(
                        (
                            f"The code **{confession_code.upper()}** doesn't refer to a given confession channel. "
                            "Please give your confession again to be able to provide a new channel code."
                        ),
                    )
                elif isinstance(confession_code, discord.TextChannel):
                    await response_channel.send(
                        f"The channel **{confession_code.mention}** doesn't refer to a given confession channel.",
                    )
            except Exception:
>>>>>>> Stashed changes
                pass
            return
        try:
            confession_channel = self.bot.get_channel(confession_channel_id) or await self.bot.fetch_channel(confession_channel_id)
        except (discord.NotFound, discord.Forbidden):
            confession_channel = None
        if confession_channel is None:
            await channel.send(f"The code `{code_message.content}` doesn't refer to a given confession channel. Please give your confession again to be able to provide a new channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass
            return

<<<<<<< Updated upstream
        # Check the user is in the guild for the channel
        if original_message.author.id not in confession_channel.guild._members:
            await channel.send(f"You're not in the guild that the channel code `{code}` refers to. Please give your confession again and provide an alternative channel code.")
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass
            return
=======
        # Verify the channel exists
        if isinstance(confession_code, str):
            confession_channel_id = confession_channel_id_rows[0]['channel_id']
            try:
                confession_channel = self.bot.get_channel(confession_channel_id) or await self.bot.fetch_channel(confession_channel_id)
            except (discord.NotFound, discord.Forbidden):
                confession_channel = None
            if confession_channel is None:
                try:
                    await response_channel.send(
                        (
                            f"The code `{confession_code.content}` doesn't refer to a given confession channel. "
                            "Please give your confession again to be able to provide a new channel code."
                        ),
                    )
                except Exception:
                    pass
                try:
                    self.currently_confessing.remove(author.id)
                except KeyError:
                    pass
                self.logger.info(f"Invalid confession channel for code received from {author.id}")
                return
        elif isinstance(confession_code, discord.TextChannel):
            confession_channel = confession_code
        self.logger.info(f"Channel code from {author.id} exists as a channel")

        # Verify the user is in the guild with the channel
        if isinstance(confession_code, str):
            try:
                guild = self.bot.get_guild(confession_channel.guild.id) or await self.bot.fetch_guild(confession_channel.guild.id)
                member = guild.get_member(author.id) or await guild.fetch_member(author.id)
            except discord.HTTPException:
                member = None
            if not member:
                try:
                    await response_channel.send(
                        (
                            f"You're not in the guild that the channel code **{confession_code.upper()}** refers to. "
                            "Please give your confession again and provide an alternative channel code."
                        ),
                    )
                except Exception:
                    pass
                try:
                    self.currently_confessing.remove(author.id)
                except KeyError:
                    pass
                self.logger.info(f"Invalid confession channel for user (not in guild) received from {author.id}")
                return
        elif isinstance(confession_code, discord.TextChannel):
            assert author.guild.id == confession_channel.guild.id
            member = author
        self.logger.info(f"Channel code from {author.id} has user in guild")
>>>>>>> Stashed changes

        # Check the user can see the confession channel
        member = confession_channel.guild.get_member(original_message.author.id)
        if confession_channel.permissions_for(member).read_messages is False:
            await channel.send(f"You're not able to read the messages that the channel `{code}` refers to.")
            try:
<<<<<<< Updated upstream
                self.currently_confessing.remove(original_message.author.id)
=======
                await response_channel.send(
                    (
                        f"You're not able to read the messages that the channel **{confession_code.upper()}** refers to. "
                        "Please give your confession again and provide an alternative channel code."
                    ),
                )
            except Exception:
                pass
            try:
                self.currently_confessing.remove(author.id)
>>>>>>> Stashed changes
            except KeyError:
                pass
            return
<<<<<<< Updated upstream

        # Check they're allowed to send messages to that guild
        if (confession_channel.guild.id, original_message.author.id) in self.bot.banned_users:
            await channel.send("You've been banned from sending messages in to that server :/")
=======
        self.logger.info(f"Channel code from {author.id} has user with permissions")

        # Verify the user isn't banned from sending in confessions
        user_is_banned = False
        for i in banned_user_rows:
            if i['guild_id'] == confession_channel.guild.id:
                user_is_banned = True
        if user_is_banned:
            try:
                await response_channel.send(
                    "You've been banned from sending messages in to that server :/",
                )
            except Exception:
                pass
>>>>>>> Stashed changes
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass
            return

        # Oh boy they are - time to send the confession I guess
        embed = discord.Embed(
            title=f"Confession Code {code.upper()}",
            description=confession,
            timestamp=dt.utcnow(),
            colour=random.randint(1, 0xffffff),
        )
        user_ban_code = get_code(16)
        self.confession_users[user_ban_code] = original_message.author
        embed.set_footer(text=f"x.banuser {user_ban_code}")
        try:
            confessed_message = await confession_channel.send(embed=embed)
        except Exception as e:
<<<<<<< Updated upstream
            await channel.send(f"I encoutered the error `{e}` trying to send in the confession :/")
=======
            await response_channel.send(
                f"I encoutered the error `{e}` trying to send in the confession :/",
            )
>>>>>>> Stashed changes
            try:
                self.currently_confessing.remove(original_message.author.id)
            except KeyError:
                pass
            return
<<<<<<< Updated upstream
        await channel.send(f"I sucessfully sent in your confession!\n{confessed_message.jump_url}")
=======
        await response_channel.send(
            f"I sucessfully sent in your confession!\n{confessed_message.jump_url}",
        )
>>>>>>> Stashed changes
        try:
            self.currently_confessing.remove(original_message.author.id)
        except KeyError:
            pass
<<<<<<< Updated upstream
        self.log_handler.info(f"Sent confession from {original_message.author.id} to {confession_channel.id} ({code: >5}) -> {confession}")

        # Log it to db
        async with self.bot.database() as db:
            await db(
                'INSERT INTO confession_log (confession_message_id, user_id, guild_id, channel_code, channel_id, timestamp, confession) VALUES ($1, $2, $3, $4, $5, $6, $7)',
                confessed_message.id,
                original_message.author.id,
                confession_channel.guild.id,
                code.lower(),
                confession_channel.id,
                confessed_message.created_at,
                confession,
=======
        self.logger.info(
            f"Sent confession from {author.id} to {confession_channel.id} "
            f"({confession_channel_id_rows[0]['code'].upper(): >5}) -> {confession}"
        )
        
        # Log their confession to the database
        async with self.bot.database() as db:
            await db(
                """INSERT INTO confession_log (confession_message_id, user_id, guild_id,
                channel_code, channel_id, timestamp, confession, ban_code) VALUES
                ($1, $2, $3, $4, $5, $6, $7, $8)""",
                confessed_message.id, author.id, confession_channel.guild.id,
                confession_channel_id_rows[0]['code'].lower(), confession_channel.id,
                discord.utils.naive_dt(confessed_message.created_at), confession, user_ban_code,
>>>>>>> Stashed changes
            )


def setup(bot:utils.CustomBot):
    x = Confession(bot)
    bot.add_cog(x)
