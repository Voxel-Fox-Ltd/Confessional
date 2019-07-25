from datetime import datetime as dt
from json import load
from asyncio import sleep, create_subprocess_exec
from glob import glob
from re import compile
from logging import getLogger
from urllib.parse import urlencode
from typing import Dict

from aiohttp import ClientSession
from discord import Game, Message, Permissions
from discord.ext.commands import AutoShardedBot, when_mentioned_or, cooldown
from discord.ext.commands.cooldowns import BucketType

from cogs.utils.database import DatabaseConnection


logger = getLogger('confession')


def get_prefix(bot, message:Message):
    '''
    Gives the prefix for the given guild
    '''

    return when_mentioned_or(bot.config['default_prefix'])(bot, message)


class CustomBot(AutoShardedBot):

    def __init__(self, config_file:str='config/config.json', commandline_args=None, *args, **kwargs):
        # Things I would need anyway
        if kwargs.get('command_prefix'):
            super().__init__(*args, **kwargs)
        else:
            super().__init__(command_prefix=get_prefix, *args, **kwargs)

        # Store the config file for later
        self.config = None
        self.config_file = config_file
        self.reload_config()
        self.commandline_args = commandline_args
        self.bad_argument = compile(r'(User|Member) "(.*)" not found')
        self._invite_link = None

        # Aiohttp session
        self.session = ClientSession(loop=self.loop)

        # Allow database connections like this
        self.database = DatabaseConnection

        # Store the startup method so I can see if it completed successfully
        self.startup_time = dt.now()
        self.startup_method = None

        # Store the confession channels for a guild
        self.confession_channels: Dict[str, int] = {}  # code: channel_id

    @property
    def code_channels(self) -> Dict[int, str]:
        return {o:i for i,o in self.confession_channels.items()}


    @property 
    def invite_link(self):
        # https://discordapp.com/oauth2/authorize?client_id=468281173072805889&scope=bot&permissions=35840&guild_id=208895639164026880
        if self._invite_link: return self._invite_link
        permissions = Permissions()
        permissions.read_messages = True 
        permissions.send_messages = True 
        permissions.embed_links = True 
        permissions.attach_files = True 
        self._invite_link = 'https://discordapp.com/oauth2/authorize?' + urlencode({
            'client_id': self.user.id,
            'scope': 'bot',
            'permissions': permissions.value
        })
        return self.invite_link


    def invite_link_to_guild(self, guild_id:int):
        return self.invite_link + f'&guild_id={guild_id}'


    async def startup(self):
        '''
        Resets and fills the FamilyTreeMember cache with objects
        '''

        # Remove caches
        logger.debug("Clearing caches")
        self.confession_channels.clear()

        # Open db 
        try:
            db: DatabaseConnection = await self.database.get_connection()
        except Exception as e:
            logger.critical(f"Exception raised on DB connect {e}")
            exit(1)

        # Get the confession channels
        try:
            con_channels = await db('SELECT * FROM guild_confession_channel')
        except Exception as e:
            logger.critical(f"Exception raised on guild_confession_channel SELECT query: {e}")
            exit(1)
        self.confession_channels = {i['code']: i['channel_id'] for i in con_channels}

        # Close db 
        await db.disconnect()

        # Wait for the bot to cache users before continuing
        logger.debug("Waiting until ready before completing startup method.")
        await self.wait_until_ready() 
        
        
    async def on_message(self, message):
        # ctx = await self.get_context(message, cls=CustomContext)
        ctx = await self.get_context(message)
        await self.invoke(ctx)


    def get_uptime(self) -> float:
        '''
        Gets the uptime of the bot in seconds
        '''

        return (dt.now() - self.startup_time).total_seconds()


    def get_extensions(self) -> list:
        '''
        Gets the filenames of all the loadable cogs
        '''

        ext = glob('cogs/[!_]*.py')
        rand = glob('cogs/utils/random_text/[!_]*.py')
        extensions = [i.replace('\\', '.').replace('/', '.')[:-3] for i in ext + rand]
        logger.debug("Getting all extensions: " + str(extensions))
        return extensions


    def load_all_extensions(self):
        '''
        Loads all extensions from .get_extensions()
        '''

        logger.debug('Unloading extensions... ')
        for i in self.get_extensions():
            log_string = f' * {i}... '
            try:
                self.unload_extension(i)
                log_string += 'sucess'
            except Exception as e:
                log_string += str(e)
            logger.debug(log_string)
        logger.debug('Loading extensions... ')
        for i in self.get_extensions():
            log_string = f' * {i}... '
            try:
                self.load_extension(i)
                log_string += 'sucess'
            except Exception as e:
                log_string += str(e)
            logger.debug(log_string)


    async def set_default_presence(self):
        '''
        Sets the default presence of the bot as appears in the config file
        '''
        
        # Update presence
        logger.debug("Setting default bot presence")
        presence_text = self.config['presence_text']
        if self.shard_count > 1:
            for i in range(self.shard_count):
                game = Game(f"{presence_text} (shard {i})")
                await self.change_presence(activity=game, shard_id=i)
        else:
            game = Game(presence_text)
            await self.change_presence(activity=game)


    def reload_config(self):
        logger.debug("Reloading config")
        with open(self.config_file) as a:
            self.config = load(a)


    def run(self):
        super().run(self.config['token'])


    async def start(self, token:str=None):
        '''Starts up the bot and whathaveyou'''

        logger.debug("Running startup method") 
        self.startup_method = self.loop.create_task(self.startup())
        logger.debug("Running original D.py start method")
        await super().start(token or self.config['token'])

    
    async def logout(self):
        '''Logs out the bot and all of its started processes'''

        logger.debug("Closing aiohttp ClientSession")
        await self.session.close()
        logger.debug("Running original D.py logout method")
        await super().logout()
