from discord.ext import commands

from cogs import utils


class Misc(utils.Cog):

    MINIMUM_PREFIX_LENGTH = 1
    MAXIMUM_PREFIX_LENGTH = 50
    
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
                       
    @commands.command(aliases=['changeprefix'])
    async def prefix(self, ctx:commands.Context, prefix:str=None):
        '''Changes the prefix of the server (or gives you set prefix)'''

        # Checks that the command was run in a discord server and not in DMs
        if ctx.guild is None:
            await ctx.send("This command does not work in DMs. Use the command on a server you have the `manage server` permission on.")

        # If no new prefix is provided, send the bot's current prefix
        if prefix is None:
            async with self.bot.database() as db:
                prefixRows = await db("SELECT * from prefix where guildid = $1", ctx.guild.id)
            await ctx.send(f"The prefix for this server is `{prefixRows[0]['prefix']}`")
            return

        # Make sure the prefix isn't too long                    
        if len(prefix) > MAXIMUM_PREFIX_LENGTH:
            await ctx.send("Could not set that as a prefix as it is longer than 50 characters.")
            return
                           
        # Make sure the prefix isn't too short
        if len(prefix) < MINIMUM_PREFIX_LENGTH:
            await ctx.send("Could not set that as a prefix as it is shorter than 1 character.")
            return

        # Checks if the command runner has the manage server permission
        if ctx.author.guild_permissions.manage_guild is False:
            await ctx.send("You are missing the `manage server` permission required to run this command.")
            return
                           
        # Add the new prefix into the DB
        async with self.bot.database() as db:
            await db("INSERT into prefix (guildid, prefix) VALUES ($1, $2) on conflict (guildid) do update set prefix = $2", ctx.guild.id, prefix)

        # Send a confirmation message
        await ctx.send(f"Set prefix to `{prefix}`")


                           
                           
def setup(bot:utils.CustomBot):
    x = Misc(bot)
    bot.add_cog(x)
