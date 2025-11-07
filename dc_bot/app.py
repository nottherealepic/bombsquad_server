import discord
from discord.ext import tasks
import os
import socket
import asyncio
import ast  # Used to safely read the player list from the server
from dotenv import load_dotenv

# --- Load Configuration from .env file ---
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# Use "if...else" to prevent errors if the ID is not set yet
STATUS_CHANNEL_ID = int(os.getenv('STATUS_CHANNEL_ID')) if os.getenv('STATUS_CHANNEL_ID') else None
STATUS_MESSAGE_ID = int(os.getenv('STATUS_MESSAGE_ID')) if os.getenv('STATUS_MESSAGE_ID') else None
TERMINAL_CHANNEL_ID = int(os.getenv('TERMINAL_CHANNEL_ID'))

BOMBSQUAD_HOST = os.getenv('BOMBSQUAD_HOST')
BOMBSQUAD_RCON_PORT = int(os.getenv('BOMBSQUAD_RCON_PORT'))
BOMBSQUAD_RCON_PASSWORD = os.getenv('BOMBSQUAD_RCON_PASSWORD')

# --- Bot Setup ---
# We need message_content intent to read commands from the terminal channel
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# --- BombSquad RCON Function ---
async def send_bs_command(command: str):
    """Connects to the BombSquad RCON, sends a command, and gets the response."""
    try:
        # Open a connection to the server
        reader, writer = await asyncio.open_connection(BOMBSQUAD_HOST, BOMBSQUAD_RCON_PORT)

        # BombSquad RCON asks for password first
        await reader.read(1024)  # Read the "Password:" prompt from the server
        writer.write((BOMBSQUAD_RCON_PASSWORD + '\n').encode('utf-8'))
        await writer.drain()

        # Now send the actual command
        writer.write((command + '\n').encode('utf-8'))
        await writer.drain()
        
        # Read the server's response
        response_data = await reader.read(4096)
        response = response_data.decode('utf-8', errors='ignore')

        # Clean up and close the connection
        writer.close()
        await writer.wait_closed()
        
        return response
    except Exception as e:
        # If connection fails, the server is likely offline
        print(f"RCON Error: Could not connect or send command. {e}")
        return None

# --- Main Bot Logic ---

@bot.event
async def on_ready():
    """This function runs when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user}')
    if STATUS_CHANNEL_ID and STATUS_MESSAGE_ID:
        # If we have the IDs, start the updating task
        update_status_embed.start()
        print("Live status updater has started.")
    else:
        print("WARNING: Status Channel/Message ID not set. Use '!setup' in a channel to create the status message.")

@tasks.loop(seconds=15)
async def update_status_embed():
    """This is the background task that updates the embed every 15 seconds."""
    if not STATUS_CHANNEL_ID or not STATUS_MESSAGE_ID:
        return # Don't run if the config is not set

    status_channel = bot.get_channel(STATUS_CHANNEL_ID)
    if not status_channel:
        print(f"Error: Cannot find status channel with ID {STATUS_CHANNEL_ID}")
        return

    try:
        status_message = await status_channel.fetch_message(STATUS_MESSAGE_ID)
    except discord.NotFound:
        print(f"Error: Cannot find status message with ID {STATUS_MESSAGE_ID}. Stopping task.")
        update_status_embed.stop()
        return

    # Get live data from the server by running the '/list' command
    server_response = await send_bs_command('/list')

    # --- Create Embed based on server status ---

    if server_response is None:
        # Server is OFFLINE
        embed = discord.Embed(
            title="Server Status: Offline",
            description=f"Could not connect to the BombSquad server.\nIt might be restarting or offline.",
            color=discord.Color.red()
        )
    else:
        # Server is ONLINE
        try:
            # The server sends the player list as a string like "[('PlayerName', 1)]"
            # ast.literal_eval safely converts this string into a real Python list
            players = ast.literal_eval(server_response.strip())
            player_count = len(players)

            embed = discord.Embed(
                title="Server Status: Online",
                description=f"Server is up and running! Join now!",
                color=discord.Color.green()
            )
            embed.add_field(name="Players", value=f"**{player_count} / 8**", inline=True) # Change 8 to your max players
            embed.add_field(name="Server IP", value=f"`{BOMBSQUAD_HOST}`", inline=True)

            if players:
                # Format the player list for the embed
                player_list_str = "\n".join([f"• {p[0]}" for p in players])
                embed.add_field(name="Players Online", value=player_list_str, inline=False)
            else:
                embed.add_field(name="Players Online", value="No players currently on the server.", inline=False)

        except Exception as e:
            # If we get a response but can't read it, show an error state
            embed = discord.Embed(
                title="Server Status: Error",
                description="Connected to the server, but the response was unreadable.",
                color=discord.Color.orange()
            )
            print(f"Error parsing server response: {e}")
    
    embed.set_footer(text="Last updated")
    embed.timestamp = discord.utils.utcnow()
    await status_message.edit(embed=embed)


@bot.event
async def on_message(message):
    """This function runs every time a message is sent in a channel the bot can see."""
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # --- Setup Command ---
    # Creates the initial status message and gives you the IDs
    if message.content.lower() == '!setup':
        placeholder_embed = discord.Embed(title="Generating status message...")
        sent_message = await message.channel.send(embed=placeholder_embed)
        
        info_text = (
            f"**Setup Complete!**\n\n"
            f"1. Copy the following lines into your `.env` file:\n"
            f"```ini\n"
            f"STATUS_CHANNEL_ID={sent_message.channel.id}\n"
            f"STATUS_MESSAGE_ID={sent_message.id}\n"
            f"```\n"
            f"2. Restart the bot (`Ctrl+C` in terminal, then run `python bs_bot.py` again)."
        )
        await message.channel.send(info_text)
        return

    # --- Terminal Command Handler ---
    if message.channel.id == TERMINAL_CHANNEL_ID:
        command = message.content
        bs_command_to_send = ""

        # Handle your special /announce command
        if command.lower().startswith('/announce '):
            # Get the text after "/announce "
            announcement_text = command[10:]
            # The BombSquad command for a global message is '/msg "Your Message"'
            bs_command_to_send = f'/msg "{announcement_text}"'
        else:
            # For all other commands, just add a / if it's not there
            bs_command_to_send = command if command.startswith('/') else f'/{command}'

        await message.add_reaction('⏳') # Show that the command is processing

        response = await send_bs_command(bs_command_to_send)

        await message.remove_reaction('⏳', bot.user)

        if response is not None:
            await message.add_reaction('✅') # Success
            # If the server sent back a response (like for /list), reply with it
            if response.strip():
                 await message.reply(f"Server Response:\n```\n{response.strip()}\n```", mention_author=False)
        else:
            await message.add_reaction('❌') # Failure
            await message.reply("Failed to send command. Server might be offline.", mention_author=False)

# --- Run the Bot ---
if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN is missing from your .env file. Bot cannot start.")
else:
    bot.run(DISCORD_TOKEN)