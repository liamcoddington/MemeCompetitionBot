#!/usr/bin/env python

import discord
import os
import random
import asyncio
import json

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.guild_reactions = True

client = discord.Client(intents=intents)

# Load the Discord bot token from the config file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    TOKEN = config.get('token', '')
    PREFIX = config.get('prefix', '')

ongoing_competitions = {}  # Dictionary to keep track of ongoing competitions

# Utility function to read meme templates from a folder
def read_meme_templates():
    meme_folder = './meme_templates/'
    return [file for file in os.listdir(meme_folder) if file.endswith('.jpg')]

# Function to start a competition
async def start_competition(channel_id, guild_id):
    global ongoing_competitions

    if guild_id in ongoing_competitions:
        await client.get_channel(channel_id).send('A competition is already running in this server.')
        return

    templates = read_meme_templates()
    random_template = random.choice(templates)
    file_location = f'{os.path.dirname(os.path.realpath(__file__))}/meme_templates/{random_template}'
    file = discord.File(file_location)
    print(f'using {file_location}')

    channel = client.get_channel(channel_id)
    await channel.send('Competition has started and submissions will stop in 20 minutes! Create a meme using this template:')
    message = await channel.send(file=file)
    competition_message_id = message.id

    # Add the competition to the ongoing competitions dictionary
    ongoing_competitions[guild_id] = {
        'channel_id': channel_id,
        'message_id': competition_message_id,
        'submissions_active': True,
        'submissions': {}
    }
    print(ongoing_competitions)

# Function to start the voting phase
async def start_voting_phase(guild_id):
    global ongoing_competitions

    if guild_id not in ongoing_competitions:
        return

    competition = ongoing_competitions[guild_id]
    competition['submissions_active'] = False

    channel = client.get_channel(competition['channel_id'])
    await channel.send('Submissions are now closed. Voting ends in 5 minutes!')
    await asyncio.sleep(5 * 60)  # 5 minutes for voting phase
    await end_voting_phase(guild_id)

# Function to end the voting phase and determine the winner
async def end_voting_phase(guild_id):
    global ongoing_competitions

    if guild_id not in ongoing_competitions:
        return

    competition = ongoing_competitions[guild_id]
    channel = client.get_channel(competition['channel_id'])

    # Determine the winner based on votes
    submissions = competition['submissions']
    winner_id = max(submissions, key=submissions.get, default=None)
    max_votes = submissions.get(winner_id, 0)

    if winner_id:
        await channel.send(f'The competition is over! The winner is <@{winner_id}> with {max_votes} votes! Congratulations!')
    else:
        await channel.send('The competition is over, but no winner was determined.')

    # Clean up the competition data
    ongoing_competitions.pop(guild_id, None)

@client.event
async def on_ready():
    print('Bot is online!')

@client.event
async def on_guild_join(guild):
    print(f'Added to server: {guild.name} (ID: {guild.id})')

@client.event
async def on_guild_remove(guild):
    print(f'Removed from server: {guild.name} (ID: {guild.id})')

@client.event
async def on_reaction_add(reaction, user):
    global ongoing_competitions

    if reaction.message.reference is None or user.bot:
        return

    guild_id = reaction.message.guild.id
    if guild_id not in ongoing_competitions:
        return

    competition = ongoing_competitions[guild_id]

    if reaction.emoji == '👍' and reaction.message.reference.message_id == competition['message_id']:
        submission_id = reaction.message.author.id
        submissions = competition['submissions']

        # Count the vote for the submission
        print(f'submission_id {submission_id} now has {reaction.count - 1} votes')
        submissions[submission_id] = reaction.count - 1

@client.event
async def on_message(message):
    global ongoing_competitions

    if message.guild.id in ongoing_competitions:
        competition = ongoing_competitions[message.guild.id]

        # Check if the message was sent in the submissions channel, is a reply, and submissions are active
        if competition['submissions_active'] and message.reference:
            # Check if the referenced message is the original competition post
            if competition['message_id'] == message.reference.message_id:
                print("counting submission")

                # Save the submission
                submission_id = message.author.id
                competition['submissions'][submission_id] = competition['submissions'].get(submission_id, 0)

                # Acknowledge the submission
                await message.add_reaction('👍')
                return

    # Check if the message starts with the "+" prefix (admin command)
    if not message.content.startswith(PREFIX) or not any(role.permissions.administrator for role in message.author.roles):
        return

    print('Message contains the prefix and was from an admin')

    args = message.content[len(PREFIX):].strip().split()
    command = args.pop(0).lower()

    if command == 'start':
        print('start command')
        guild_id = message.guild.id
        await start_competition(message.channel.id, guild_id)

        # Set a timer for 20 minutes (1200 seconds) to stop accepting submissions
        await asyncio.sleep(1200)
        await start_voting_phase(guild_id)

client.run(TOKEN)
