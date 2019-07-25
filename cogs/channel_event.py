from discord import TextChannel

from cogs.utils.custom_bot import CustomBot
from cogs.utils.custom_cog import Cog 


class ChannelEvent(Cog):

    def __init__(self, bot:CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot 


    @Cog.listener('on_guild_channel_delete')
    async def channel_delete_listener(self, channel):
        '''Checks to see if a tracked channel is being deleted'''

        # Check for text channel
        if not isinstance(channel, TextChannel):
            return 

        # Check for existing
        code = self.bot.code_channels.get(channel.id)
        if code is None:
            return 
        
        # It exists
        self.log_handler.info(f"Deleting inaccessible channel with ID {channel.id} and code {code.upper()}")
        async with self.bot.database() as db:
            await db('DELETE FREOM confession_channel WHERE channel_id=$1', channel.id)
        del self.bot.confession_channels[code]


def setup(bot:CustomBot):
    x = ChannelEvent(bot)
    bot.add_cog(x)
