import os
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, Embed, ui
from datetime import timedelta
import aiosqlite
from webserver import keep_alive
import io

TOKEN = os.environ['TOKEN']
WELCOME_CHANNEL_ID = 1276071491791753217
LOG_CHANNEL_ID = 1276076861541056592
intents = nextcord.Intents.all()
client = commands.Bot(command_prefix="?", intents=intents, help_command=None)

# List of guild IDs where the bot will work
GUILD_IDS = [1276070927452602439]  # Replace with your guild IDs

@client.event
async def on_ready():
    print(f'Bot is ready. Logged in as {client.user.name}')


# Ban command
@client.slash_command(name="ban", description="Ban a member", guild_ids=GUILD_IDS)
@commands.has_permissions(ban_members=True)
async def ban(interaction: Interaction, member: nextcord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f'{member.mention} has been banned for: {reason}')

# Kick command
@client.slash_command(name="kick", description="Kick a member", guild_ids=GUILD_IDS)
@commands.has_permissions(kick_members=True)
async def kick(interaction: Interaction, member: nextcord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f'{member.mention} has been kicked for: {reason}')

# Timeout command
@client.slash_command(name="timeout", description="Timeout a member", guild_ids=GUILD_IDS)
@commands.has_permissions(moderate_members=True)
async def timeout(interaction: Interaction, member: nextcord.Member, time: int = SlashOption(description="Time in minutes"), reason: str = "No reason provided"):
    duration = timedelta(minutes=time)
    await member.timeout_for(duration=duration, reason=reason)
    await interaction.response.send_message(f'{member.mention} has been timed out for {time} minutes for: {reason}')

# Mute command
@client.slash_command(name="mute", description="Mute a member", guild_ids=GUILD_IDS)
@commands.has_permissions(moderate_members=True)
async def mute(interaction: Interaction, member: nextcord.Member, time: int = SlashOption(description="Time in minutes"), reason: str = "No reason provided"):
    duration = timedelta(minutes=time)
    await member.timeout_for(duration=duration, reason=reason)
    await interaction.response.send_message(f'{member.mention} has been muted for {time} minutes for: {reason}')

# Unmute command
@client.slash_command(name="unmute", description="Unmute a member", guild_ids=GUILD_IDS)
@commands.has_permissions(moderate_members=True)
async def unmute(interaction: Interaction, member: nextcord.Member):
    await member.remove_timeout()
    await interaction.response.send_message(f'{member.mention} has been unmuted.')

# Unban command
@client.slash_command(name="unban", description="Unban a member", guild_ids=GUILD_IDS)
@commands.has_permissions(ban_members=True)
async def unban(interaction: Interaction, user_id: int, reason: str = "No reason provided"):
    user = await client.fetch_user(user_id)
    await interaction.guild.unban(user, reason=reason)
    await interaction.response.send_message(f'{user.mention} has been unbanned.')

# Purge command
@client.slash_command(name="purge", description="Delete a number of messages", guild_ids=GUILD_IDS)
@commands.has_permissions(manage_messages=True)
async def purge(interaction: Interaction, number: int):
    await interaction.channel.purge(limit=number)
    await interaction.response.send_message(f'Deleted {number} messages.', ephemeral=True)

# Lock command
@client.slash_command(name="lock", description="Lock a channel", guild_ids=GUILD_IDS)
@commands.has_permissions(manage_channels=True)
async def lock(interaction: Interaction, channel: nextcord.TextChannel = SlashOption(description="Select the channel to lock", required=True)):
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message(f'{channel.mention} has been locked.')

# Unlock command
@client.slash_command(name="unlock", description="Unlock a channel", guild_ids=GUILD_IDS)
@commands.has_permissions(manage_channels=True)
async def unlock(interaction: Interaction, channel: nextcord.TextChannel = SlashOption(description="Select the channel to unlock", required=True)):
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message(f'{channel.mention} has been unlocked.')

# Ticket Dropdown
class TicketDropdown(ui.Select):
    def __init__(self):
        options = [
            nextcord.SelectOption(label='Order A Bot', description='If you\'d like to order a bot, please select this option to proceed.', emoji='🤖'),
            nextcord.SelectOption(label='Order A GFX', description='If you\'d like to order a GFX, please select this option to proceed.', emoji='🎨'),
            nextcord.SelectOption(label='Order A Render', description='If you\'d like to order a render, please select this option to proceed.', emoji='🖼️')
        ]
        super().__init__(placeholder='Select an option...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: Interaction):
        selected_option = self.values[0]

        # Connect to the database
        conn = await aiosqlite.connect('ticket.db')
        cursor = await conn.cursor()

        # Create table if it doesn't exist
        await cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number INTEGER
        )
        ''')

        # Retrieve the latest ticket number
        await cursor.execute('SELECT ticket_number FROM tickets ORDER BY id DESC LIMIT 1')
        result = await cursor.fetchone()

        latest_ticket_number = result[0] if result else 0  # Start at 0 if no tickets exist

        # Increment the ticket number
        new_ticket_number = latest_ticket_number + 1

        # Format the ticket number with leading zeros (e.g., 0001)
        formatted_ticket_number = f'{new_ticket_number:04}'
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True)
        }
        # Create the text channel
        channel_name = f'ticket-{formatted_ticket_number}'
        channel = await interaction.guild.create_text_channel(channel_name, overwrites=overwrites)

        # Insert the new ticket number into the database
        await cursor.execute('INSERT INTO tickets (ticket_number) VALUES (?)', (new_ticket_number,))
        await conn.commit()
        await conn.close()

        # Create the embed with buttons
        embed = nextcord.Embed(title='Ticket Panel', description=f'Selected option: {selected_option}')
        view = ui.View()

        # Define the buttons
        close_button = nextcord.ui.Button(label='Close', style=nextcord.ButtonStyle.red, emoji='❌')
        claim_button = nextcord.ui.Button(label='Claim', style=nextcord.ButtonStyle.green, emoji='🛠️')
        transcript_button = nextcord.ui.Button(label='Transcript', style=nextcord.ButtonStyle.blurple, emoji='📜')

        # Define the callback functions for the buttons
        async def close_callback(interaction: Interaction):
            await channel.delete()
            await interaction.response.send_message('Ticket closed!')

        async def claim_callback(interaction: Interaction):
            await interaction.response.send_message('Ticket claimed!')

        async def transcript_callback(interaction: nextcord.Interaction):
            # Retrieve the channel where the interaction was triggered
            channel = interaction.channel

            # Create a list to hold the transcript messages
            transcript = []

            # Fetch the last 100 messages (or more if needed)
            async for message in channel.history(limit=1000, oldest_first=True):
                transcript.append(f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.display_name}: {message.content}")

            # Join the list into a single string with newlines
            transcript_str = "\n".join(transcript)

            # Create a file-like object from the transcript string
            transcript_file = nextcord.File(io.BytesIO(transcript_str.encode()), filename="transcript.txt")

            # Send the transcript file to the interaction's channel
            await interaction.response.send_message("Here is the transcript of this channel:", file=transcript_file)

        # Add the buttons to the view
        close_button.callback = close_callback
        claim_button.callback = claim_callback
        transcript_button.callback = transcript_callback
        view.add_item(close_button)
        view.add_item(claim_button)
        view.add_item(transcript_button)

        # Send the embed with buttons to the channel
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f'Ticket channel created: {channel.mention}', ephemeral=True)

# Setup command
@client.slash_command(name='setup', description='Set up a new ticket panel with dropdown options', guild_ids=GUILD_IDS)
async def setup(interaction: Interaction):
    dropdown = TicketDropdown()
    view = ui.View()
    view.add_item(dropdown)

    embed = nextcord.Embed(title="Ticket Creation",
          description="Select an option from the dropdown menu",
          colour=0xffffff)

    embed.set_author(name="Quantum Ticket Creation",
     icon_url="https://cdn.discordapp.com/attachments/1276072995672162304/1276470346521907321/New_Project_57.png?ex=66c9a526&is=66c853a6&hm=c821b79fe7acfebc0884645e1ab7e317a67b4d7a7403f52e00dced4360c22715&")

    embed.set_image(url="https://cdn.discordapp.com/attachments/1276072995672162304/1276470461701820477/New_Project_58.png?ex=66c9a541&is=66c853c1&hm=aa4bd4e114f186ed2728a77dd5d7bfa5680a2d6e74e8421fdc5d80ed535c1338&")

    embed.set_footer(text="Quantum Bot",
     icon_url="https://cdn.discordapp.com/attachments/1276072995672162304/1276470346521907321/New_Project_57.png?ex=66c9a526&is=66c853a6&hm=c821b79fe7acfebc0884645e1ab7e317a67b4d7a7403f52e00dced4360c22715&")

    await interaction.channel.send(embed=embed, view=view)



ROLE_ID = 1276071574084124732

@client.event
async def on_member_join(member: nextcord.Member):
    # Send a welcome message in a specific channel
    welcome_channel = client.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(f'Welcome to the server, {member.mention}!')

    # Optionally, send a DM to the member
    try:
        await member.send(f'Hi {member.name}, welcome to our Discord server!')
    except Exception as e:
        print(f"Couldn't send DM to {member.name}: {e}")

    # Add a role to the new member
    role = nextcord.utils.get(member.guild.roles, id=ROLE_ID)
    if role:
        try:
            await member.add_roles(role)
            print(f'Assigned {role.name} role to {member.name}.')
        except Exception as e:
            print(f"Couldn't assign role to {member.name}: {e}")

    # Log the event
    log_channel = client.get_channel(LOG_CHANNEL_ID)  # Replace with your log channel ID
    await log_channel.send(f'{member} has joined the server.')
@client.event
async def on_member_remove(member: nextcord.Member):
    # Send a farewell message in a specific channel
    farewell_channel = client.get_channel(WELCOME_CHANNEL_ID)  # Replace with your farewell channel ID
    await farewell_channel.send(f'{member.name} has left the server.')

    # Log the event
    log_channel = client.get_channel(LOG_CHANNEL_ID)  # Replace with your log channel ID
    await log_channel.send(f'{member} has left the server.')


@client.slash_command(name="prices", description="Get the current prices of services", guild_ids=GUILD_IDS)
async def prices(interaction: Interaction):
    # Check if the user is an administrator
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Create the embed object
    embed = nextcord.Embed(
        title="Pricing",
        description="Here are the current prices for our services:",
        color=0xFFFFFF
    )

    # Add fields for each service
    embed.add_field(
        name="Card Bot",
        value="2500 Robux",
        inline=False
    )
    embed.add_field(
        name="Sign Bot",
        value="2000 Robux",
        inline=False
    )
    embed.add_field(
        name="Custom Bot",
        value="Starting from 600 Robux",
        inline=False
    )
    embed.add_field(
        name="GFX",
        value="200 to 1000 Robux",
        inline=False
    )
    embed.add_field(
        name="Render",
        value="60 Robux",
        inline=False
    )
    embed.add_field(
        name="Logo",
        value="300 Robux",
        inline=False
    )

    # Add images for visual appeal
    embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/1276072995672162304/1276470346521907321/New_Project_57.png?ex=66c9a526&is=66c853a6&hm=c821b79fe7acfebc0884645e1ab7e317a67b4d7a7403f52e00dced4360c22715&')  # Replace with your thumbnail image URL
    embed.set_image(url='https://cdn.discordapp.com/attachments/1276072995672162304/1276574612058013787/prices_2.png?ex=66ca0641&is=66c8b4c1&hm=099e6a1753b02732fc1a5a3f76bce16eb0bb7578101e476e9ca470d298463417&')  # Replace with your main image URL

    # Send the embed
    await interaction.channel.send(embed=embed)
    
keep_alive()
client.run(TOKEN)
