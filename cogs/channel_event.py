import discord

from cogs import utils


class ChannelEvent(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot


    @utils.Cog.listener('on_guild_channel_delete')
    async def channel_delete_listener(self, channel:discord.TextChannel):
        '''Checks to see if a tracked channel is being deleted'''

        # Check for text channel
        if not isinstance(channel, discord.TextChannel):
            return

        # Check for existing
        code = self.bot.code_channels.get(channel.id)
        if code is None:
            return

        # It exists
        self.log_handler.info(f"Deleting inaccessible channel with ID {channel.id} and code {code.upper()}")
        async with self.bot.database() as db:
            await db('DELETE FROM confession_channel WHERE channel_id=$1', channel.id)
        del self.bot.confession_channels[code]


def setup(bot:utils.CustomBot):
    x = ChannelEvent(bot)
    bot.add_cog(x)
