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

    @commands.command(aliases=['server', 'support'])
    async def guild(self, ctx:commands.Context):
        '''Gives you the link to the support server'''

        await ctx.send(f"{self.bot.config['guild_invite']}")

    @commands.command(aliases=['github'])
    async def git(self, ctx:commands.Context):
        '''Gives you the link to bot's GitHub'''

        await ctx.send(f"<https://github.com/4Kaylum/Confession>")                   
                       
                       

def setup(bot:utils.CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
