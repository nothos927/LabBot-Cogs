"""discord red-bot autoreply"""
import discord, discord.utils
import asyncio
from redbot.core import checks, commands, Config
from redbot.core.utils.menus import menu, prev_page, next_page

CUSTOM_CONTROLS = {"⬅️": prev_page, "➡️": next_page}


class AutoReplyCog(commands.Cog):
    """AutoReply Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=377212919068229633005)

        default_guild_config = {
            "triggers": {}, # trigger: str response
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        triggers = await self.config.guild(message.guild).triggers()

        for trigger in triggers:
            if trigger.lower() == message.content.lower():
                await message.channel.send(triggers[trigger])

# Command groups

    @checks.admin()
    @commands.group(name='autoreply', pass_context=True)
    async def _autoreply(self, ctx):
        """Automatically reply to messages matching certain trigger phrases"""
        pass

# Commands

    @_autoreply.command(name='add')
    async def _add(self, ctx, trigger:str = '', response:str = ''):
        """Add autoreply trigger"""
        if not trigger and not response:
            message_object = await ctx.send("Let's set up an autoreply trigger. Please enter the phrase you want this autoreply to trigger on")

            def reply_check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for('message', check=reply_check, timeout=5*60)
            except asyncio.TimeoutError:
                await message_object.delete()
                return
            else:
                trigger = msg.content

            message_object1 = await ctx.send('Please enter the response for this trigger')

            try:
                msg = await self.bot.wait_for('message', check=reply_check, timeout=5*60)
            except asyncio.TimeoutError:
                await message_object1.delete()
                await message_object.delete()
                return
            else:
                response = msg.content

        async with self.config.guild(ctx.guild).triggers() as triggers:
            triggers[trigger] = response

        await ctx.send('✅ Autoreply trigger successfully added')

    @commands.guild_only()
    @_autoreply.command(name='view')
    async def _view(self, ctx):
        """View the configuration for the autoreply cog"""
        triggers = await self.ordered_list_from_config(ctx.guild)
        embed_list = [self.make_trigger_embed(ctx, triggers[i], {'current': i+1, 'max': len(triggers)}) for i in range(len(triggers))]

        if len(embed_list) > 1:
            await menu(ctx, pages=embed_list, controls=CUSTOM_CONTROLS, message=None, page=0, timeout=5*60)

        elif len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])

        else:
            error_embed = self.make_error_embed(ctx, error_type='NoConfiguration')
            await ctx.send(embed=error_embed)

    @commands.guild_only()
    @_autoreply.command(name='remove', aliases=['delete'])
    async def _remove(self, ctx, num:int):
        """Remove a reaction pair
        
        Example:
        - `[p]autoreply remove <index>`
        To find the index of an autoreply pair do `[p]autoreply view`
        """
        l = await self.ordered_list_from_config(ctx.guild)
        to_del = l[num-1]
        embed = self.make_trigger_embed(ctx, to_del)
        message_object = await ctx.send(embed=embed, content='Are you sure you want to remove this autoreply trigger?')

        emojis = ['✅', '❌']
        for i in emojis:
            await message_object.add_reaction(i)

        def reaction_check(reaction, user):
            return (user == ctx.author) and (reaction.message.id == message_object.id) and (reaction.emoji in emojis)

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=180.0, check=reaction_check)
        except asyncio.TimeoutError:
            try:
                await message_object.clear_reactions()
            except Exception:
                pass
            return
        else:
            if reaction.emoji == '❌':
                await message_object.clear_reactions()
                return

            await message_object.clear_reactions()
            await self.remove_trigger(ctx.guild, to_del['trigger'], to_del['response'])
            success_embed = self.make_removal_success_embed(ctx, to_del)
            await ctx.send(embed=success_embed)

# Helper functions

    async def remove_trigger(self, guild: discord.Guild, trigger: str, response: str):
        async with self.config.guild(guild).triggers() as triggers:
            if trigger in triggers:
                del triggers[trigger]

    async def ordered_list_from_config(self, guild):
        async with self.config.guild(guild).triggers() as triggers:
            return [{'trigger': i, 'response': triggers[i]} for i in triggers]

    def make_error_embed(self, ctx, error_type: str = ''):
        error_msgs = {
            'NoConfiguration': 'No configuration has been set for this guild'
        }
        error_embed = discord.Embed(title='Error', description=error_msgs[error_type], colour=ctx.guild.me.colour)
        return error_embed

    def make_removal_success_embed(self, ctx, trigger_dict: dict):
        trigger = trigger_dict['trigger'][:1010] if len(trigger_dict['trigger']) > 1010 else trigger_dict['trigger']
        response = trigger_dict['response'][:1010] if len(trigger_dict['response']) > 1010 else trigger_dict['response']
        desc = f"**Trigger:**\n{trigger}\n**Response:**\n{response}"
        embed = discord.Embed(title='Autoreply trigger removed', description=desc, colour=ctx.guild.me.colour)
        return embed

    def make_trigger_embed(self, ctx, trigger_dict: dict, index={}):
        trigger = trigger_dict['trigger'][:1010] if len(trigger_dict['trigger']) > 1010 else trigger_dict['trigger']
        response = trigger_dict['response'][:1010] if len(trigger_dict['response']) > 1010 else trigger_dict['response']
        desc = f"**Trigger:**\n{trigger}\n**Response:**\n{response}"
        embed = discord.Embed(description=desc, colour=ctx.guild.me.colour)
        if index:
            embed.set_footer(text=f"{index['current']} of {index['max']}")
        return embed