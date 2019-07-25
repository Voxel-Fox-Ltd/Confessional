from discord.ext.commands import command, Context

from cogs.utils.custom_bot import CustomBot
from cogs.utils.custom_cog import Cog


class Misc(Cog):

    def __init__(self, bot:CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot

    
    @command()
    async def invite(self, ctx:Context):
        '''Gives you the invite for the bot'''

        await ctx.send(f"<{self.bot.invite_link}>")


def setup(bot:CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
