from discord.ext import commands

from cogs import utils


class Misc(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot


    @commands.command()
    async def invite(self, ctx:commands.Context):
        '''Gives you the invite for the bot'''

        await ctx.send(f"<{self.bot.invite_link}>")


def setup(bot:utils.CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
