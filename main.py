import csv
import os
from time import localtime, strftime

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())

if not os.path.exists('attendance.csv'):
    with open('attendance.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Channel Category', 'Name', 'Committee', 'Country', 'Present or Present and Voting', 'Time'])

if not os.path.exists('votes.csv'):
    with open('votes.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Channel Category', 'Name', 'Committee', 'Country', 'Vote', 'Time'])

# Dictionaries of the form {message_1: {member_1: [reaction, time], ...,member_n: [reaction, time]}, ...
#                          , message_n: {member_1: [reaction, time], ...,member_n: [reaction, time]}}
attendance = {}
votes = {}
# Lists of Ids of allowed emojis
attendance_emojis = [799426659706077185, 799426658808889364]
vote_emojis = [799422476396134470, 799425285531500565, 799953931366694912]
no_abstain_emojis = [799422476396134470, 799425285531500565]

pv_members = {}
pres_and_vote = 799426659706077185

guild_id = 0 #Replace with guild ID

# Variables made global in functions
no_abstain = False

@bot.event
async def on_ready():
    guild = bot.get_guild(guild_id)
    bot.my_guild = guild
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

#    if message.author.id == 676031194592444418 and message.channel.category.name == 'Bot':
#        await message.channel.send("I'm watching you")

    await bot.process_commands(message)


@bot.event
async def on_command(ctx):
    if ctx.channel not in pv_members:
        pv_members[ctx.channel] = []


@bot.event
async def on_command_completion(ctx):
    await ctx.message.delete(delay=2)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if reaction.message in attendance:
        if reaction.custom_emoji and reaction.emoji.id in attendance_emojis:
            member = bot.my_guild.get_member(user.id)
            time = strftime('%H:%M:%S', localtime())
            if member in attendance[reaction.message]:
                old_reaction = attendance[reaction.message][member][0]
                if old_reaction != reaction:
                    await old_reaction.remove(user)
            attendance[reaction.message][member] = [reaction, time]
        else:
            await reaction.remove(user)

    elif reaction.message in votes:
        if no_abstain or user in pv_members[reaction.message.channel]:
            emojis = no_abstain_emojis
        else:
            emojis = vote_emojis

        if reaction.custom_emoji and reaction.emoji.id in emojis:
            member = bot.my_guild.get_member(user.id)
            time = strftime('%H:%M:%S', localtime())
            if member in votes[reaction.message]:
                old_reaction = votes[reaction.message][member][0]
                if old_reaction != reaction:
                    await old_reaction.remove(user)
            votes[reaction.message][member] = [reaction, time]
        else:
            await reaction.remove(user)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(f"Role '{error.missing_role}' is required to run this command")
    elif isinstance(error, commands.MissingPermissions):
        if len(error.missing_perms) == 1:
            plural, verb = '', 'is'
        else:
            plural, verb = 's', 'are'
        missing_perms = ', '.join(repr(perm) for perm in error.missing_perms)
        await ctx.send(f"Permission{plural} {missing_perms} {verb} required to run this command")


@bot.command(help='@mention note_content – Sends a message to the person mentioned')
async def note(ctx, member: discord.Member, *, note):
    await ctx.message.delete()
    country = ctx.author.nick.split(' | ')[1].split(' ', 1)[1]
    await member.send(f'{country}: {note}')


@bot.command(help='Starts roll call')
@commands.has_role('Chair')
async def roll(ctx):
    message = await ctx.send('Please react to this message with Present <:PV:799426658808889364> '
                             'or Present & Voting <:PRES:799426659706077185>.')
    attendance[message] = {}
    for emoji_id in attendance_emojis:
        emoji = bot.get_emoji(emoji_id)
        await message.add_reaction(emoji)


@bot.command(name='endroll', help='Ends roll call and adds data to a file')
@commands.has_role('Chair')
async def end_roll(ctx):
    category = ctx.channel.category
    for message in attendance:
        if message.channel == ctx.channel:
            break
    
    with open("attendance.csv", "a", newline="") as file:
        writer = csv.writer(file)
        for member, details in attendance[message].items():
            name, committee_country = member.nick.split(" | ")
            committee, country = committee_country.split(' ', 1)
            reaction, time = details
            reaction_name = reaction.emoji.name
            writer.writerow([category, name, committee, country, reaction_name, time])

            if reaction.emoji.id == pres_and_vote:
                pv_members[ctx.channel].append(member)

    del attendance[message]

    message = await ctx.channel.fetch_message(message.id)
    emoji_names = {'PRES': 'Present', 'PV': 'Present and Voting'}
    for reaction in message.reactions:
        emoji_name = reaction.emoji.name
        await ctx.send(f'{emoji_names[emoji_name]}: {reaction.count - 1}')


@bot.command(help='Starts voting procedure')
@commands.has_role('Chair')
async def vote(ctx):
    await ctx.invoke(clear)
    message = await ctx.send('To vote on this resolution please react to this message with '
                             'For <:FOR:799422476396134470>, Against <:AGAINST:799425285531500565> or '
                             'Abstain <:ABSTAIN:799953931366694912>.')
    votes[message] = {}
    for emoji_id in vote_emojis:
        emoji = bot.get_emoji(emoji_id)
        await message.add_reaction(emoji)


@bot.command(help='Starts a motion to divide the house (Use this before .endvote)')
@commands.has_role('Chair')
async def mdiv(ctx):
    await ctx.invoke(clear)
    global no_abstain
    no_abstain = True
    message = await ctx.send('Motion to Divide the House: You can only vote on this resolution with '
                             'For <:FOR:799422476396134470> or Against <:AGAINST:799425285531500565>.')
    votes[message] = {}
    for emoji_id in no_abstain_emojis:
        emoji = bot.get_emoji(emoji_id)
        await message.add_reaction(emoji)


@bot.command(name='endvote', help='Ends voting procedure and adds data to a file')
@commands.has_role('Chair')
async def end_vote(ctx):
    global no_abstain
    no_abstain = False
    category = ctx.channel.category
    for message in votes:
        if message.channel == ctx.channel:
            break

    with open("votes.csv", "a", newline="") as file:
        writer = csv.writer(file)
        for member, details in votes[message].items():
            name, committee_country = member.nick.split(" | ")
            committee, country = committee_country.split(' ', 1)
            reaction, time = details
            reaction_name = reaction.emoji.name
            writer.writerow([category, name, committee, country, reaction_name, time])

    if ctx.channel in pv_members:
        del pv_members[ctx.channel]
    del votes[message]

    message = await ctx.channel.fetch_message(message.id)
    for reaction in message.reactions:
        await ctx.send(f'{reaction.emoji.name.title()}: {reaction.count - 1}')


@bot.command(help='Clears attendance/vote data without adding it to a file')
@commands.has_role('Chair')
async def clear(ctx):
    global no_abstain
    no_abstain = False
    for message in votes:
        if message.channel == ctx.channel:
            del votes[message]
            break
    for message in attendance:
        if message.channel == ctx.channel:
            del attendance[message]
            break


@end_roll.error
async def end_roll_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send('.roll must be used before .endroll')


@end_vote.error
async def end_vote_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send('.vote must be used before .endvote')

bot.run(TOKEN)
