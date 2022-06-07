import string
import random
import asyncio
import re
from datetime import datetime as dt
import typing

import discord
from discord.ext import commands
import voxelbotutils as vbu


def get_code(n: int = 5) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


class Confession(vbu.Cog):

    def __init__(self, bot: vbu.Bot):
        super().__init__(bot)
        self.currently_confessing = set()  # A set rather than a list because it uses a hash table

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
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def banuser(self, ctx: vbu.Context, uuid: str):
        """
        Bans a user from being able to send in any more confessions to your server.
        """

        # See if a user was pinged
        try:
            user_to_ban = await commands.MemberConverter().convert(ctx, uuid)
        except commands.BadArgument:
            user_to_ban = None

        # See if a code was given
        if user_to_ban is None and len(uuid) != 16:
            return await ctx.send("You've not posted a valid ID - please give a ban code from a confession.")

        # See if the code was valid
        if user_to_ban is None:
            async with self.bot.database() as db:
                data = await db("SELECT * FROM confession_log WHERE ban_code=$1", uuid)
                if not data:
                    return await ctx.send("The ID provided doesn't refer to a user. Please try again.")
                user_to_ban = discord.Object(data[0]['user_id'])

        # Ban the given user
        async with self.bot.database() as db:
            await db('INSERT INTO banned_users (guild_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING', ctx.guild.id, user_to_ban.id)

        # Respond
        try:
            await user_to_ban.send(f"You've been banned from posting confessions on the server **{ctx.guild.name}** (`{ctx.guild.id}`). Your identity is still a secret. Don't worry about it too much.")
        except (discord.HTTPException, AttributeError):
            pass
        await ctx.send("That user has been banned from sending in more confessions on your server.")

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
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def unbanuser(self, ctx: vbu.Context, user_id: vbu.converters.UserID):
        """
        Unbans a user from messaging the confessional on your server.
        """

        async with self.bot.database() as db:
            await db("DELETE FROM banned_users WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, user_id)
        await ctx.send(
            f"<@{user_id}> has been unbanned from sending in messages, if they were even banned at all.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

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
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    @commands.guild_only()
    async def createchannel(self, ctx: vbu.Context, code: str = None):
        """
        Creates a confession channel for the bot to run responses to.
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

        # Create a channel with that name
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True),
        }
        channel = await ctx.guild.create_text_channel(
            f"confessional-{code}",
            reason="Confessional channel created",
            topic=f"A confessional channel for use with {ctx.guild.me.mention}. The code for this channel is \"{code.upper()}\". DM the bot your confession, and then provide \"{code.upper()}\" as your channel code when it's asked for.",
            overwrites=overwrites,
        )

        # And done
        async with self.bot.database() as db:
            await db("INSERT INTO confession_channel VALUES ($1, $2)", code, channel.id)
        await ctx.send(f"Your new confessional channel has been created over at {channel.mention}! Just DM me your confession, give the channel code **{code.upper()}**, and that'll be that!")

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

    @vbu.Cog.listener('on_message')
    async def confession_listener(self, message: discord.Message):
        """
        Listens out for a message in a DM channel and assumes it's a confession.
        """

        # Handle message replies - DM the author of a confession if a reply was gotten
        if not isinstance(message.channel, discord.DMChannel):
            reference = message.reference
            if not reference:
                return
            async with self.bot.database() as db:
                posted_message = await db("SELECT * FROM confession_log WHERE confession_message_id=$1", reference.message_id)
            if not posted_message:
                return
            try:
                self.logger.info(f"Sending message for confession reply to {posted_message[0]['user_id']}")
                confessed_user = await self.bot.fetch_user(posted_message[0]['user_id'])
                await confessed_user.send(f"Your confession in **{message.guild.name}** has been replied to!\n{message.jump_url}")
                self.logger.info(f"Sent message to {posted_message[0]['user_id']}")
            except discord.HTTPException:
                self.logger.info(f"Coud not send message to {posted_message[0]['user_id']}")
                pass
            return

        # Ignore bots
        if message.author.bot:
            return

        # Ignore if they author is currently confessing
        if message.author.id in self.currently_confessing:
            return

        # Check the confession they want to seng
        confession = message.content
        if len(confession) > 1000:
            return await message.channel.send(
                "Your confession can only be 1000 characters - please shorten it and try again.",
                ephemeral=True,
            )
        elif message.attachments:
            return await message.channel.send(
                "I don't support sending images right now.",
                ephemeral=True,
            )

        # Okay it should be alright - add em to the cache
        self.currently_confessing.add(message.author.id)

        # Ask the user for a channel code
        self.logger.info(f"Received valid confession text from {message.author.id} - asking for channel")
        await message.channel.send("What's the code for the channel you want to confess to?")
        try:
            code_message = await self.bot.wait_for(
                "message",
                check=lambda m: isinstance(m.channel, discord.DMChannel) and m.author.id == message.author.id,
                timeout=120,
            )
        except asyncio.TimeoutError:
            try:
                await message.channel.send(
                    "The timer for you to give a channel code has timed out. Please give your confession again to be able to provide another.",
                    ephemeral=True,
                )
            except Exception:
                pass
            try:
                self.currently_confessing.remove(message.author.id)
            except KeyError:
                pass
            return
        self.logger.info(f"Received confession code from {message.author.id} - checking exists")

        # Actually send the confession
        await self.send_confession(
            response_channel=message.channel,
            author=message.author,
            confession=confession,
            confession_code=code_message.content,
        )
        try:
            self.currently_confessing.remove(message.author.id)
        except KeyError:
            pass

    async def send_confession(
            self, response_channel: discord.abc.Messageable, author: discord.User, confession: str,
            confession_code: typing.Union[str, discord.TextChannel]):
        """
        The actual process of sending in a confession to the channel.
        """

        # Get the channel ID and check if the user is banned
        async with self.bot.database() as db:
            if isinstance(confession_code, str):
                confession_channel_id_rows = await db(
                    "SELECT * FROM confession_channel WHERE LOWER(code)=LOWER($1)",
                    confession_code,
                )
            elif isinstance(confession_code, discord.TextChannel):
                confession_channel_id_rows = await db(
                    "SELECT * FROM confession_channel WHERE channel_id=$1",
                    confession_code.id,
                )
            banned_user_rows = await db("SELECT * FROM banned_users WHERE user_id=$1", author.id)
        self.logger.info(f"Received confession code data from database from {author.id} - validating")

        # Verify the channel code is real
        if not confession_channel_id_rows:
            try:
                if isinstance(confession_code, str):
                    await response_channel.send(
                        (
                            f"The code **{confession_code.upper()}** doesn't refer to a given confession channel. "
                            "Please give your confession again to be able to provide a new channel code."
                        ),
                        ephemeral=True,
                    )
                elif isinstance(confession_code, discord.TextChannel):
                    await response_channel.send(
                        f"The channel **{confession_code.mention}** doesn't refer to a given confession channel.",
                        ephemeral=True,
                    )
            except Exception:
                pass
            try:
                self.currently_confessing.remove(author.id)
            except KeyError:
                pass
            self.logger.info(f"Invalid confession code received from {author.id}")
            return

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
                        ephemeral=True,
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
                        ephemeral=True,
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

        # Verify the user can read messages in that confession channel
        if confession_channel.permissions_for(member).read_messages is False:
            try:
                await response_channel.send(
                    (
                        f"You're not able to read the messages that the channel **{confession_code.upper()}** refers to. "
                        "Please give your confession again and provide an alternative channel code."
                    ),
                    ephemeral=True,
                )
            except Exception:
                pass
            try:
                self.currently_confessing.remove(author.id)
            except KeyError:
                pass
            self.logger.info(f"Invalid confession channel for user (no read messages) received from {author.id}")
            return
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
                    ephemeral=True,
                )
            except Exception:
                pass
            try:
                self.currently_confessing.remove(author.id)
            except KeyError:
                pass
            self.logger.info(f"Invalid confession channel for user (banned) received from {author.id}")
            return
        self.logger.info(f"Channel code from {author.id} has user unbanned")

        # See if the confession is a reply to a previous confession
        confession = confession.strip()
        reply_message = None
        end_match = re.search(
            (
                r"https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
                r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})$"
            ),
            confession,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        if end_match:
            try:
                reply_message = await confession_channel.fetch_message(int(end_match.group("message")))
                confession = re.sub(
                    (
                        r"https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
                        r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})$"
                    ),
                    "",
                    confession,
                    flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
                )
            except discord.HTTPException:
                pass
        if reply_message is None:
            end_match = re.search(
                (
                    r"^https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
                    r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})"
                ),
                confession,
                re.MULTILINE | re.DOTALL | re.IGNORECASE,
            )
            if end_match:
                try:
                    reply_message = await confession_channel.fetch_message(int(end_match.group("message")))
                    confession = re.sub(
                        (
                            r"^https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
                            r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})"
                        ),
                        "",
                        confession,
                        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
                    )
                except discord.HTTPException:
                    pass
        confession = confession.strip()

        # Generate the embed to send
        embed = vbu.Embed(
            title=f"Confession Code {confession_channel_id_rows[0]['code'].upper()}",
            description=confession,
            timestamp=dt.utcnow(),
            use_random_colour=True,
        )
        user_ban_code = get_code(16)
        embed.set_footer(text=f"/banuser {user_ban_code}")

        # Try and send the confession
        try:
            confessed_message = await confession_channel.send(embed=embed, reference=reply_message)
        except Exception as e:
            await response_channel.send(
                f"I encoutered the error `{e}` trying to send in the confession :/",
                ephemeral=not isinstance(response_channel, (discord.DMChannel, discord.TextChannel)),
            )
            try:
                self.currently_confessing.remove(author.id)
            except KeyError:
                pass
            self.logger.info(f"Invalid send to channel - {e}")
            return
        await response_channel.send(
            f"I sucessfully sent in your confession!\n{confessed_message.jump_url}",
            ephemeral=not isinstance(response_channel, (discord.DMChannel, discord.TextChannel)),
        )
        try:
            self.currently_confessing.remove(author.id)
        except KeyError:
            pass
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
            )


def setup(bot: vbu.Bot):
    x = Confession(bot)
    bot.add_cog(x)
