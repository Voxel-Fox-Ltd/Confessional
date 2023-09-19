import string
import random
from datetime import datetime as dt
from uuid import UUID

import novus as n
from novus.ext import client, database as db


def get_code(n: int = 5) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


class Confession(client.Plugin):

    @client.command(
        options=[
            n.ApplicationCommandOption(
                name="user",
                type=n.ApplicationOptionType.string,
                description="The UUID of a confession, a user ping, or a user ID.",
            ),
        ],
        default_member_permissions=n.Permissions(manage_messages=True),
        dm_permission=False,
    )
    async def banuser(self, ctx: n.types.CommandI, user: str):
        """
        Bans a user from being able to send in any more confessions to your
        server.
        """

        # Set up who we want to ban
        user_to_ban: n.User | n.GuildMember | n.Object | None = None
        assert ctx.guild is not None

        # See if it was a user ID
        if user.isdigit():
            user_to_ban = n.Object(user)
        elif user.startswith("@") and ctx.data.resolved.members:
            user_to_ban = list(ctx.data.resolved.members.values())[0]
        else:
            # try:
            #     UUID(user)
            # except ValueError:
            #     return await ctx.send(
            #         "That is not a confession ID, user ID, or user ping.",
            #         ephemeral=True,
            #     )
            async with db.Database.acquire() as conn:
                data = await conn.fetch(
                    """
                    SELECT
                        *
                    FROM
                        confession_log
                    WHERE
                        ban_code = $1
                        AND guild_id = $2
                    """,
                    user,
                    ctx.guild.id,
                )
                if not data and not user_to_ban:
                    return await ctx.send(
                        "The ID provided doesn't seem to exist and no user was found.",
                        ephemeral=True,
                    )
                user_to_ban = n.Object(data[0]['user_id'])

        assert user_to_ban

        # Ban the given user
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    banned_users
                    (
                        guild_id,
                        user_id
                    )
                VALUES
                    (
                        $1,
                        $2
                    )
                ON CONFLICT
                DO NOTHING
                """,
                ctx.guild.id,
                user_to_ban.id,
            )

        # And done
        await ctx.send(
            (
                "That user has been banned from sending in more confessions "
                "on your server."
            ),
            ephemeral=True,
        )

    @client.command(
        options = [
            n.ApplicationCommandOption(
                name="message_id",
                type=n.ApplicationOptionType.string,
                description="The ID of a confession message"
            ),
        ],
        default_member_permissions=n.Permissions(manage_messages=True),
        dm_permission=False,
    )
    async def get_ban_command(
            self,
            ctx: n.types.CommandI,
            message_id: str
        ):
        """
        Sends a copyable ban command for a message sent by Confessional.

        This should be run in the channel of the target message.
        """
        assert ctx.channel # No DMs
        
        message = await ctx.channel.fetch_message(message_id)

        assert message # We have a message
        assert message.author.id == self.bot.me.id # Confessional sent it
        assert message.embeds # It has an embed
        assert message.embed[0].footer # The first embed has a footer

        return await ctx.send(message.embeds[0].footer, ephemeral=True)

    @client.command(
        options=[
            n.ApplicationCommandOption(
                name="user",
                type=n.ApplicationOptionType.user,
                description="The user who you want to unban.",
            ),
        ],
        default_member_permissions=n.Permissions(manage_messages=True),
        dm_permission=False,
    )
    async def unbanuser(
            self,
            ctx: n.types.CommandI,
            user: n.User | n.GuildMember):
        """
        Unbans a user from messaging the confessional on your server.
        """

        assert ctx.guild is not None
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM
                    banned_users
                WHERE
                    guild_id = $1
                    AND user_id = $2
                """,
                ctx.guild.id,
                user.id,
            )
        await ctx.send(
            (
                f"{user.mention} has been unbanned from sending in messages, "
                "if they were even banned at all."
            ),
            allowed_mentions=n.AllowedMentions.none(),
        )

    @client.command(
        name="channel create",
        options=[],
        default_member_permissions=n.Permissions(manage_guild=True),
        dm_permission=False,
    )
    async def channel_create(
            self,
            ctx: n.types.CommandI):
        """
        Creates a confession channel for the bot to run responses to.
        """

        # Check their code is valid, or provide a new one
        async with db.Database.acquire() as conn:
            while True:
                code = get_code()
                rows = await conn.fetch(
                    """
                    SELECT
                        *
                    FROM
                        confession_channel
                    WHERE
                        code=$1
                    """,
                    code
                )
                if not rows:
                    break

        # Get the data we need for the guild
        assert ctx.guild is not None
        guild: n.Guild
        roles: list[n.Role]
        if isinstance(ctx.guild, n.Guild):
            guild = ctx.guild
            roles = guild.roles
        else:
            guild = await n.Guild.fetch(ctx.state, ctx.guild.id)
            roles = await guild.fetch_roles()
        try:
            default_role = [i for i in roles if i.id == guild.id][0]
        except IndexError:
            raise AssertionError("This literally isn't possible")

        # Create a channel with that name
        me = await ctx.state.user.get_current_user()
        overwrites = [
            n.PermissionOverwrite(
                default_role.id,
                n.PermissionOverwriteType.role,
                allow=n.Permissions(read_messages=True),
                deny=n.Permissions(send_messages=False),
            ),
            n.PermissionOverwrite(
                me.id,
                n.PermissionOverwriteType.member,
                allow=n.Permissions(read_messages=True, send_messages=True),
            ),
        ]
        channel = await guild.create_channel(
            name=f"confessional-{code}",
            type=n.ChannelType.guild_text,
            topic=(
                f"A confessional channel for use with {me.mention}. "
                f"The code for this channel is \"{code.upper()}\"."
            ),
            permission_overwrites=overwrites,
            reason="Confessional channel created",
        )

        # And done
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    confession_channel
                VALUES
                    (
                        $1,
                        $2
                    )
                """,
                code, channel.id,
            )
        await ctx.send(
            (
                f"Your new confessional channel has been created at "
                f"{channel.mention}!"
            ),
        )

    @client.command(
        name="channel set",
        options=[
            n.ApplicationCommandOption(
                name="channel",
                type=n.ApplicationOptionType.channel,
                description="The channel that you want to make into a confession channel.",
                channel_types=[
                    n.ChannelType.guild_text,
                    n.ChannelType.announcement_thread,
                    n.ChannelType.guild_announcement,
                    n.ChannelType.guild_voice,
                    n.ChannelType.public_thread,
                ],
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
        dm_permission=False,
    )
    async def channel_set(
            self,
            ctx: n.types.CommandI,
            channel: n.Channel):
        """
        Sets a confession channel for the bot to run responses to.
        """

        # Check their code is valid, or provide a new one
        async with db.Database.acquire() as conn:
            while True:
                code = get_code()
                rows = await conn.fetch(
                    """
                    SELECT
                        *
                    FROM
                        confession_channel
                    WHERE
                        code=$1
                    """,
                    code
                )
                if not rows:
                    break

        # And done
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    confession_channel
                VALUES
                    (
                        $1,
                        $2
                    )
                """,
                code, channel.id,
            )
        await ctx.send(
            (
                f"Your new confessional channel has been set at "
                f"{channel.mention}!"
            ),
        )

    @client.command(
        options=[
            n.ApplicationCommandOption(
                name="channel",
                type=n.ApplicationOptionType.channel,
                description="The channel that you want to confess into.",
                channel_types=[
                    n.ChannelType.guild_text,
                    n.ChannelType.announcement_thread,
                    n.ChannelType.guild_announcement,
                    n.ChannelType.guild_voice,
                    n.ChannelType.public_thread,
                ],
            ),
            n.ApplicationCommandOption(
                name="confession",
                type=n.ApplicationOptionType.string,
                description="Your confession :)",
            ),
        ],
        default_member_permissions=n.Permissions(manage_guild=True),
        dm_permission=False,
    )
    async def confess(
            self,
            ctx: n.types.CommandI,
            channel: n.Channel,
            confession: str):
        """
        Send a message over to a confession channel.
        """

        assert ctx.guild

        async with db.Database.acquire() as conn:
            confession_channel_id_rows = await conn.fetch(
                """
                SELECT
                    *
                FROM
                    confession_channel
                WHERE
                    channel_id = $1
                """,
                channel.id,
            )
            if not confession_channel_id_rows:
                return await ctx.send(
                    "That is not set up as a confession channel.",
                    ephemeral=True,
                )
            banned_user_rows = await conn.fetch(
                """
                SELECT
                    *
                FROM
                    banned_users
                WHERE
                    user_id = $1
                    AND guild_id = $2
                """,
                ctx.user.id,
                ctx.guild.id,
            )
            if banned_user_rows:
                return await ctx.send(
                    "You've been banned from sending messages in to that server :/",
                    ephemeral=True,
                )
        self.log.info(f"Received confession code data from database from {ctx.user.id} - validating")

        # # See if the confession is a reply to a previous confession
        # confession = confession.strip()
        # reply_message = None
        # end_match = re.search(
        #     (
        #         r"https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
        #         r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})$"
        #     ),
        #     confession,
        #     re.MULTILINE | re.DOTALL | re.IGNORECASE,
        # )
        # if end_match:
        #     try:
        #         reply_message = await confession_channel.fetch_message(int(end_match.group("message")))
        #         confession = re.sub(
        #             (
        #                 r"https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
        #                 r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})$"
        #             ),
        #             "",
        #             confession,
        #             flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        #         )
        #     except discord.HTTPException:
        #         pass
        # if reply_message is None:
        #     end_match = re.search(
        #         (
        #             r"^https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
        #             r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})"
        #         ),
        #         confession,
        #         re.MULTILINE | re.DOTALL | re.IGNORECASE,
        #     )
        #     if end_match:
        #         try:
        #             reply_message = await confession_channel.fetch_message(int(end_match.group("message")))
        #             confession = re.sub(
        #                 (
        #                     r"^https?:\/\/(?:(?:canary|ptb)?\.)?discord(?:app)?\.com\/channels\/"
        #                     r"(?P<guild>\d{16,23})\/(?P<channel>\d{16,23})\/(?P<message>\d{16,23})"
        #                 ),
        #                 "",
        #                 confession,
        #                 flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
        #             )
        #         except discord.HTTPException:
        #             pass
        # confession = confession.strip()

        # Generate the embed to send
        embed = n.Embed(
            description=confession,
            timestamp=dt.utcnow(),
        )
        user_ban_code = get_code(16)
        embed.set_footer(text=f"/banuser {user_ban_code}")

        # Try and send the confession
        try:
            confessed_message = await channel.send(
                embeds=[embed],
                # reference=reply_message,
            )
        except Exception as e:
            await ctx.send(
                f"I encoutered the error `{e}` trying to send in the confession :/",
                ephemeral=True,
            )
            self.log.info(f"Invalid send to channel - {e}")
            return
        await ctx.send(
            f"I sucessfully sent in your confession!\n{confessed_message.jump_url}",
            ephemeral=True,
        )
        self.log.info(
            f"Sent confession from {ctx.user.id} to {channel.id} -> {confession}"
        )

        # Log their confession to the database
        async with db.Database.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO
                    confession_log
                    (
                        confession_message_id,
                        user_id,
                        guild_id,
                        channel_code,
                        channel_id,
                        timestamp,
                        confession,
                        ban_code
                    )
                VALUES
                    (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6,
                        $7,
                        $8
                    )
                """,
                confessed_message.id,
                ctx.user.id,
                ctx.guild.id,
                confession_channel_id_rows[0]['code'].lower(),
                channel.id,
                dt.utcnow(),
                confession,
                user_ban_code,
            )
