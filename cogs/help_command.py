import discord
from discord.ext import commands

from cogs import utils


HELP_TEXT = """Simply PM me your confession, and then I'll ask for your confession code, which is the set of letters associated with the channel! Your confession will be anonymously copied right over, and nobody will ever know who said what, not even the server moderators.

`{ctx.prefix}createchannel <code>` -> Creates a confession channel for you to use on your server. If you don't provide a code (ie you run just `{ctx.prefix}createchannel`), a random code will be used.
`{ctx.prefix}banuser code` -> Bans a user from sending in any confessions. Users cannot be unbanned with a code, so make sure you know what you're doing when you run this.
`{ctx.prefix}unbanuser @User` -> Unbans a user from sending in confessions.
`{ctx.prefix}invite` -> Gives you the invite link for the bot! Add me to your own server!
`{ctx.prefix}support` -> Get an invite to the support server.
`{ctx.prefix}donate` -> Bots cost money to keep alive - donate to help out with its upkeep!"""


class HelpCommand(utils.Cog):

    def __init__(self, bot:utils.CustomBot):
        super().__init__(self.__class__.__name__)
        self.bot = bot
        self.original_help_command = self.bot.get_command("help")
        self.bot.remove_command("help")

    def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.original_help_command)

    @commands.command(name="help")
    async def help2(self, ctx:commands.Context):
        """The new improved help command"""

        try:
            await ctx.author.send(HELP_TEXT)
        except discord.Forbidden:
            await ctx.send("I wasn't able to send you a DM :c")
            return
        await ctx.send("Send you a DM!")


def setup(bot:utils.CustomBot):
    x = HelpCommand(bot)
    bot.add_cog(x)
