# cooldown edit confirmed

import discord
from discord import app_commands
...


import discord
from discord import app_commands
from discord.ext import commands
from web3 import Web3
from discord.utils import get
import asyncio
import time
import json
import os
from discord.ui import View, Button, Select
from decimal import Decimal
from colorama import Fore, Style, init, Back
init(autoreset=True)


w3 = Web3(Web3.HTTPProvider("https://babel-api.mainnet.iotex.io"))
if w3.provider is None:
    print("No provider set for Web3")


ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    }
]


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


YOUR_GUILD_ID = 1351992245615853708
LOADING_EMOJI = "<a:loading:1352356646579339348>"
YOUR_BOT_OWNER_ID = 1079887553429246002


DATA_DIR = "data"
VERIFIED_FILE = os.path.join(DATA_DIR, "verified.json")
ROLE_THRESHOLDS_FILE = os.path.join(DATA_DIR, "role_thresholds.json")
CONFIG_FILE = os.path.join(DATA_DIR, "bot_config.json")


if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Created data directory at {DATA_DIR}")


if os.path.exists(VERIFIED_FILE):
    with open(VERIFIED_FILE, 'r') as f:
        verified_wallets = json.load(f)
        print(f"{Back.LIGHTBLUE_EX}   LOG   {Back.RESET} Loaded verified wallets: {len(verified_wallets)} guilds")
else:
    verified_wallets = {}
    with open(VERIFIED_FILE, 'w') as f:
        json.dump(verified_wallets, f)
    print("Initialized empty verified wallets file")

if os.path.exists(ROLE_THRESHOLDS_FILE):
    with open(ROLE_THRESHOLDS_FILE, 'r') as f:
        role_thresholds = json.load(f)
        print(f"{Back.LIGHTBLUE_EX}   LOG   {Back.RESET} Loaded role thresholds: {len(role_thresholds)} guilds")
else:
    role_thresholds = {}
    with open(ROLE_THRESHOLDS_FILE, 'w') as f:
        json.dump(role_thresholds, f, indent=4)
    print("Initialized empty role thresholds file")

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        bot_config = json.load(f)
        print(f"Loaded bot config: {len(bot_config)} guilds")
else:
    bot_config = {}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(bot_config, f, indent=4)
    print("Initialized empty bot config file")

pending_verifications = {}


def save_verified_wallets():
    with open(VERIFIED_FILE, 'w') as f:
        json.dump(verified_wallets, f, indent=4)
    print("Saved verified wallets to file")

def save_role_thresholds():
    with open(ROLE_THRESHOLDS_FILE, 'w') as f:
        json.dump(role_thresholds, f, indent=4)
    print("Saved role thresholds to file")

def save_bot_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(bot_config, f, indent=4)
    print("Saved bot config to file")

async def send_log(guild_id: str, title: str, description: str, user: discord.User = None):
    print(f"{Back.YELLOW}   LOG   {Back.RESET} Attempting to send log to guild {guild_id}: {title}")
    if guild_id in bot_config and "logs_channel" in bot_config[guild_id]:
        channel = bot.get_channel(bot_config[guild_id]["logs_channel"])
        if channel and isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            if user:
                embed.set_footer(text=f"Initiated by {user.name}#{user.discriminator} ({user.id})")
            else:
                embed.set_footer(text="Initiated by Bot")
            try:
                await channel.send(embed=embed)
                print(f"{Back.GREEN}   LOG   {Back.RESET} Successfully sent log to guild {guild_id}: {title}")
            except Exception as e:
                print(f"Error sending log to guild {guild_id}: {e}")
        else:
            print(f"Invalid logs channel for guild {guild_id}")
    else:
        print(f"No logs channel configured for guild {guild_id}")

def get_token_contract(token_address):
    print(f"{Back.GREEN}   LOG   {Back.RESET} Creating contract instance for token address: {token_address}")
    return w3.eth.contract(address=w3.to_checksum_address(token_address), abi=ERC20_ABI)


class CopyAddressView(View):
    @discord.ui.button(label="Copy Address", emoji="📋", style=discord.ButtonStyle.primary)
    async def copy_address(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        print(f"CopyAddressView triggered by user {interaction.user.id} in guild {guild_id}")
        bot_wallet = bot_config[guild_id]["bot_wallet"]
        await interaction.response.send_message("**To copy on mobile, hold down and click Copy.**", ephemeral=True)
        await interaction.followup.send(f"{bot_wallet}\n", ephemeral=True)
        print(f"Sent bot wallet address to user {interaction.user.id}")
        self.stop()

class ConfigView(View):
    def __init__(self, original_interaction: discord.Interaction):
        super().__init__(timeout=60)
        self.original_interaction = original_interaction
        print(f"ConfigView initialized for user {original_interaction.user.id}")

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary)
    async def config_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        print(f"Config logs selected by user {interaction.user.id} in guild {guild_id}")
        if guild_id not in bot_config:
            bot_config[guild_id] = {}
        await interaction.response.send_message("Please send the logs channel ID.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            channel_id = int(message.content.strip())
            channel = interaction.guild.get_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                await interaction.followup.send("Invalid text channel ID.", ephemeral=True)
                await message.delete()
                print(f"Invalid channel ID {channel_id} provided by user {interaction.user.id}")
                return
            bot_config[guild_id]["logs_channel"] = channel_id
            save_bot_config()
            await send_log(guild_id, "Logs Channel Set", f"Set to <#{channel_id}>.", interaction.user)
            await interaction.delete_original_response()
            await message.delete()
            print(f"Logs channel set to {channel_id} for guild {guild_id}")
        except (ValueError, asyncio.TimeoutError) as e:
            await interaction.followup.send("Invalid ID or timeout.", ephemeral=True)
            print(f"Error in config_logs for guild {guild_id}: {e}")

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary)
    async def config_token(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        print(f"Config token selected by user {interaction.user.id} in guild {guild_id}")
        if guild_id not in bot_config:
            bot_config[guild_id] = {}
        await interaction.response.send_message("Please send the token contract address.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            token_address = message.content.strip().lower()
            if not w3.is_address(token_address):
                await interaction.followup.send("Invalid address.", ephemeral=True)
                await message.delete()
                print(f"Invalid token address {token_address} provided by user {interaction.user.id}")
                return
            contract = get_token_contract(token_address)
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()
            name = contract.functions.name().call()
            bot_config[guild_id].update({
                "token_address": token_address,
                "decimals": decimals,
                "token_symbol": symbol,
                "token_name": name
            })
            save_bot_config()
            await send_log(guild_id, "Token Set", f"Address: `{token_address}`, Symbol: {symbol}, Name: {name}, Decimals: {decimals}", interaction.user)
            await interaction.delete_original_response()
            await message.delete()
            print(f"Token configured for guild {guild_id}: {token_address}")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)
            await message.delete()
            print(f"Error in config_token for guild {guild_id}: {e}")

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary)
    async def config_bot_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        print(f"Config bot wallet selected by user {interaction.user.id} in guild {guild_id}")
        if guild_id not in bot_config:
            bot_config[guild_id] = {}
        await interaction.response.send_message("Please send the bot wallet address.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            bot_wallet = message.content.strip().lower()
            if not w3.is_address(bot_wallet):
                await interaction.followup.send("Invalid address.", ephemeral=True)
                await message.delete()
                print(f"Invalid bot wallet address {bot_wallet} provided by user {interaction.user.id}")
                return
            bot_config[guild_id]["bot_wallet"] = bot_wallet
            save_bot_config()
            await send_log(guild_id, "Bot Wallet Set", f"Set to `{bot_wallet}`.", interaction.user)
            await interaction.delete_original_response()
            await message.delete()
            print(f"Bot wallet set to {bot_wallet} for guild {guild_id}")
        except asyncio.TimeoutError:
            await interaction.followup.send("Timeout.", ephemeral=True)
            print(f"Timeout in config_bot_wallet for guild {guild_id}")

    @discord.ui.button(label="4", style=discord.ButtonStyle.primary)
    async def config_verification_amount(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        print(f"Config verification amount selected by user {interaction.user.id} in guild {guild_id}")
        if guild_id not in bot_config or "token_address" not in bot_config[guild_id]:
            await interaction.response.send_message("Set the token address first (option 2).", ephemeral=True)
            print(f"Token address not set for guild {guild_id}")
            return
        decimals = bot_config[guild_id]["decimals"]
        symbol = bot_config[guild_id]["token_symbol"]
        await interaction.response.send_message(f"Send the verification amount (e.g., 1.5 for 1.5 {symbol}).", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            amount = float(message.content.strip())
            if amount <= 0:
                raise ValueError("Amount must be positive")
            verification_amount = int(Decimal(str(amount)) * Decimal(10 ** decimals))
            bot_config[guild_id]["verification_amount"] = verification_amount
            save_bot_config()
            await send_log(guild_id, "Verification Amount Set", f"Set to {amount} {symbol} ({verification_amount} units).", interaction.user)
            await interaction.delete_original_response()
            await message.delete()
            print(f"Verification amount set to {amount} {symbol} for guild {guild_id}")
        except (ValueError, asyncio.TimeoutError) as e:
            await interaction.followup.send("Invalid amount or timeout.", ephemeral=True)
            print(f"Error in config_verification_amount for guild {guild_id}: {e}")

    @discord.ui.button(label="5", style=discord.ButtonStyle.primary)
    async def config_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Configure Roles",
            description="Choose an option:\n- Start Blank: Add a new role manually\n- Detect Roles: Add all server roles with default threshold",
            color=discord.Color.blue()
        )
        view = ConfigureRolesView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ConfigureRolesView(View):
    @discord.ui.button(label="Start Blank", style=discord.ButtonStyle.primary)
    async def start_blank(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        guild = interaction.guild
        await interaction.response.send_message("Please send the role name.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            role_name = message.content.strip()
            await message.delete()
            discord_role = get(guild.roles, name=role_name) or await guild.create_role(name=role_name)
            await interaction.followup.send("Please send the minimum token amount.", ephemeral=True)
            message = await bot.wait_for("message", check=check, timeout=60)
            min_amount = int(message.content.strip())
            await message.delete()
            role_thresholds.setdefault(guild_id, {})[role_name] = min_amount
            save_role_thresholds()
            await send_log(guild_id, "Role Added", f"Added role '{role_name}' with threshold {min_amount}.", interaction.user)
            await interaction.followup.send(f"Added role '{role_name}' with threshold {min_amount}.", ephemeral=True)
        except (ValueError, asyncio.TimeoutError):
            await interaction.followup.send("Invalid input or timeout.", ephemeral=True)

    @discord.ui.button(label="Detect Roles", style=discord.ButtonStyle.primary)
    async def detect_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild.id)
        guild = interaction.guild
        existing_roles = role_thresholds.get(guild_id, {})
        for role in guild.roles:
            if role.name not in existing_roles:
                role_thresholds.setdefault(guild_id, {})[role.name] = 1
        save_role_thresholds()
        roles = role_thresholds.get(guild_id, {})
        embed = discord.Embed(
            title="Configured Roles",
            description="\n".join([f"{role}: {amount}" for role, amount in roles.items()]),
            color=discord.Color.blue()
        )
        view = RoleListView(roles, guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class RoleListView(View):
    def __init__(self, roles, guild_id):
        super().__init__(timeout=60)
        self.roles = list(roles.keys())
        self.guild_id = guild_id
        options = [discord.SelectOption(label=role) for role in self.roles]
        select = discord.ui.Select(placeholder="Choose a role", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        selected_role = interaction.data['values'][0]
        embed = discord.Embed(
            title=f"Configure Role: {selected_role}",
            description=f"Current threshold: {role_thresholds[self.guild_id][selected_role]}\nChoose an action:",
            color=discord.Color.blue()
        )
        view = RoleConfigView(selected_role, self.guild_id, self)
        await interaction.response.edit_message(embed=embed, view=view)

class RoleConfigView(View):
    def __init__(self, role_name, guild_id, role_list_view):
        super().__init__(timeout=60)
        self.role_name = role_name
        self.guild_id = guild_id
        self.role_list_view = role_list_view

    @discord.ui.button(label="Change Token Amount", style=discord.ButtonStyle.primary)
    async def change_amount(self, interaction, button):
        await interaction.response.send_message(f"Please send the new token amount for role '{self.role_name}'.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            message = await bot.wait_for("message", check=check, timeout=60)
            new_amount = int(message.content.strip())
            await message.delete()
            role_thresholds[self.guild_id][self.role_name] = new_amount
            save_role_thresholds()
            await send_log(self.guild_id, "Role Modified", f"Updated '{self.role_name}' to {new_amount}.", interaction.user)
            embed = discord.Embed(
                title="Configured Roles",
                description="\n".join([f"{role}: {amount}" for role, amount in role_thresholds[self.guild_id].items()]),
                color=discord.Color.blue()
            )
            await interaction.followup.send(f"Updated '{self.role_name}' to {new_amount}.", ephemeral=True)
            await interaction.message.edit(embed=embed, view=self.role_list_view)
        except (ValueError, asyncio.TimeoutError):
            await interaction.followup.send("Invalid amount or timeout.", ephemeral=True)

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger)
    async def remove_role(self, interaction, button):
        if self.role_name in role_thresholds[self.guild_id]:
            del role_thresholds[self.guild_id][self.role_name]
            if not role_thresholds[self.guild_id]:
                del role_thresholds[self.guild_id]
            save_role_thresholds()
            await send_log(self.guild_id, "Role Removed", f"Removed '{self.role_name}'.", interaction.user)
            embed = discord.Embed(
                title="Configured Roles",
                description="\n".join([f"{role}: {amount}" for role, amount in role_thresholds.get(self.guild_id, {}).items()]) or "No roles configured.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(f"Removed '{self.role_name}'.", ephemeral=True)
            await interaction.message.edit(embed=embed, view=self.role_list_view)
        else:
            await interaction.response.send_message(f"Role '{self.role_name}' not found.", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        embed = discord.Embed(
            title="Configured Roles",
            description="\n".join([f"{role}: {amount}" for role, amount in role_thresholds.get(self.guild_id, {}).items()]) or "No roles configured.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self.role_list_view)

# Background tasks
async def monitor_transactions():
    while True:
        try:
            print("Starting transaction monitoring loop")
            token_addresses = set(config.get("token_address") for config in bot_config.values() if "token_address" in config)
            print(f"Monitoring token addresses: {token_addresses}")
            filters = {}
            for token_address in token_addresses:
                contract = get_token_contract(token_address)
                bot_wallets = [config["bot_wallet"] for config in bot_config.values() if config.get("token_address") == token_address and "bot_wallet" in config]
                print(f"{Back.GREEN}   LOG   {Back.RESET} Bot wallets for {token_address}: {bot_wallets}")
                if bot_wallets:
                    transfer_filter = contract.events.Transfer.create_filter(
                        from_block="latest",
                        argument_filters={"to": [w3.to_checksum_address(addr) for addr in bot_wallets]}
                    )
                    filters[token_address] = transfer_filter
                    print(f"{Back.GREEN}   LOG   {Back.RESET} Transfer filter created for {token_address}")

            while True:
                await asyncio.sleep(10)
                current_time = time.time()
                print(f"{Back.GREEN}   LOG   {Back.RESET} Checking pending verifications and events at {current_time}")
                for addr, (interaction, status_message, start_time) in list(pending_verifications.items()):
                    guild_id = str(interaction.guild.id)
                    if guild_id not in bot_config or "verification_amount" not in bot_config[guild_id]:
                        print(f"Skipping {addr} due to incomplete config for guild {guild_id}")
                        continue
                    amount = bot_config[guild_id]["verification_amount"] / (10 ** bot_config[guild_id]["decimals"])
                    symbol = bot_config[guild_id]["token_symbol"]
                    bot_wallet = bot_config[guild_id]["bot_wallet"]
                    status_embed = discord.Embed(
                        title=f"Verify your {symbol} holdings :money_with_wings: {LOADING_EMOJI}",
                        description=f"Send **{amount} {symbol}** to:\n```\n{bot_wallet}\n```\nYour Wallet:\n```\n{addr}\n```",
                        color=discord.Color.blue()
                    )
                    status_embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
                    await status_message.edit(embed=status_embed)
                    print(f"Updated status embed for {addr} in guild {guild_id}")

                for token_address, transfer_filter in filters.items():
                    events = transfer_filter.get_new_entries()
                    print(f"{Back.GREEN}   LOG   {Back.RESET} Found {len(events)} new transfer events for {token_address}")
                    for event in events:
                        from_addr = event["args"]["from"].lower()
                        to_addr = event["args"]["to"].lower()
                        value = event["args"]["value"]
                        print(f"Transfer event: from {from_addr} to {to_addr}, value {value}")
                        if from_addr in pending_verifications:
                            interaction, status_message, _ = pending_verifications[from_addr]
                            guild_id = str(interaction.guild.id)
                            print(f"Pending verification found for {from_addr} in guild {guild_id}")
                            if (guild_id in bot_config and
                                bot_config[guild_id].get("token_address") == token_address and
                                bot_config[guild_id].get("bot_wallet", "").lower() == to_addr and
                                value == bot_config[guild_id]["verification_amount"]):
                                print(f"Verification conditions met for {from_addr}")
                                contract = get_token_contract(token_address)
                                decimals = bot_config[guild_id]["decimals"]
                                symbol = bot_config[guild_id]["token_symbol"]
                                balance = contract.functions.balanceOf(w3.to_checksum_address(from_addr)).call()
                                print(f"Balance of {from_addr}: {balance}")
                                guild = interaction.guild
                                member = interaction.user
                                roles_to_assign = [
                                    role_name for role_name, min_amount in role_thresholds.get(guild_id, {}).items()
                                    if balance >= min_amount * (10 ** decimals)
                                ]
                                assigned = []
                                for role_name in roles_to_assign:
                                    role = get(guild.roles, name=role_name)
                                    if role:
                                        try:
                                            await member.add_roles(role)
                                            assigned.append(role_name)
                                            print(f"Assigned role {role_name} to {member.id}")
                                        except discord.Forbidden:
                                            print(f"Missing permissions to assign role {role_name} to {member.id}")
                                        except Exception as e:
                                            print(f"Error assigning role {role_name}: {e}")
                                status_embed = discord.Embed(
                                    title="Holdings Verified! :white_check_mark:",
                                    description=f"**Roles Assigned:**\n```\n{', '.join(assigned) or 'None'}\n```",
                                    color=discord.Color.green()
                                )
                                status_embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
                                await status_message.edit(embed=status_embed)
                                print(f"Verification completed for {from_addr}")
                                verified_wallets.setdefault(guild_id, {})[from_addr] = {
                                    "username": f"{member.name}#{member.discriminator}",
                                    "last_verified": time.time(),
                                    "balance": balance
                                }
                                save_verified_wallets()
                                await send_log(
                                    guild_id,
                                    "Wallet Verified",
                                    f"Wallet: `{from_addr}`\nRoles: {', '.join(assigned) or 'None'}\nBalance: {balance / (10 ** decimals)} {symbol}",
                                    member
                                )
                                del pending_verifications[from_addr]
                            else:
                                print(f"Verification failed for {from_addr}: conditions not met")
                                status_embed = discord.Embed(
                                    title="Verification Failed",
                                    description="Incorrect amount or destination.",
                                    color=discord.Color.red()
                                )
                                status_embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
                                await status_message.edit(embed=status_embed)
                                del pending_verifications[from_addr]
        except Exception as e:
            print(f"Error in monitor_transactions: {e}")
            await asyncio.sleep(10)

async def check_timeouts():
    while True:
        await asyncio.sleep(60)
        current_time = time.time()
        print(f"{Back.GREEN}   LOG   {Back.RESET} Checking for timeouts at {current_time}")
        to_remove = [addr for addr, (_, _, start_time) in pending_verifications.items() if current_time - start_time > 600]
        for addr in to_remove:
            interaction, status_message, _ = pending_verifications[addr]
            guild_id = str(interaction.guild.id)
            print(f"Removing timed out verification for {addr} in guild {guild_id}")
            status_embed = discord.Embed(
                title="Verification Timed Out",
                description="Please try again.",
                color=discord.Color.red()
            )
            status_embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
            await status_message.edit(embed=status_embed)
            del pending_verifications[addr]

# Commands
@tree.command(name="sync", description="Sync commands globally")
async def sync_commands(interaction: discord.Interaction):
    print(f"Sync command triggered by user {interaction.user.id}")
    if interaction.user.id != YOUR_BOT_OWNER_ID:
        await interaction.response.send_message("No permission.", ephemeral=True)
        print(f"User {interaction.user.id} lacks permission for /sync")
        return
    await tree.sync()
    await interaction.response.send_message("Commands synced globally.", ephemeral=True)
    print("Commands synced globally")

@tree.command(name="config", description="Configure bot settings")
@app_commands.checks.has_permissions(manage_guild=True)
async def config(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    print(f"Config command triggered by user {interaction.user.id} in guild {guild_id}")
    embed = discord.Embed(
        title="Bot Configuration",
        description="Select an option:\n1. Configure Logs Channel\n2. Set Token Address\n3. Set Bot Wallet\n4. Set Verification Amount\n5. Configure Roles",
        color=discord.Color.blue()
    )
    view = ConfigView(interaction)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    print(f"Sent config embed to user {interaction.user.id}")

@tree.command(name="verify", description="Verify your wallet and get roles")
async def verify(interaction: discord.Interaction, wallet_address: str):
    print(f"Received /verify command from user {interaction.user.id} with wallet: {wallet_address}")
    await interaction.response.defer()
    guild_id = str(interaction.guild.id)
    print(f"Guild ID: {guild_id}")
    if guild_id not in bot_config or "token_address" not in bot_config[guild_id] or "bot_wallet" not in bot_config[guild_id]:
        print(f"Configuration incomplete for guild {guild_id}")
        await interaction.followup.send("Bot configuration incomplete. Set token address and bot wallet with /config.", ephemeral=True)
        return
    wallet_address = wallet_address.lower()
    if not w3.is_address(wallet_address):
        print(f"Invalid wallet address provided: {wallet_address}")
        embed = discord.Embed(title="Invalid Address", description="Provide a valid IoTeX address.", color=discord.Color.red())
        embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
        await interaction.followup.send(embed=embed)
        return
    if wallet_address in verified_wallets.get(guild_id, {}):
        print(f"Wallet {wallet_address} already verified in guild {guild_id}")
        embed = discord.Embed(title="Already Verified", description="Use /checkwallets to update roles.", color=discord.Color.green())
        embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
        await interaction.followup.send(embed=embed)
        return
    if wallet_address in pending_verifications:
        print(f"Verification already pending for wallet {wallet_address}")
        embed = discord.Embed(title="Pending Verification", description="Verification already in progress.", color=discord.Color.red())
        embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
        await interaction.followup.send(embed=embed)
        return
    amount = bot_config[guild_id]["verification_amount"] / (10 ** bot_config[guild_id]["decimals"])
    symbol = bot_config[guild_id]["token_symbol"]
    bot_wallet = bot_config[guild_id]["bot_wallet"]
    print(f"Preparing verification embed: Send {amount} {symbol} to {bot_wallet}")
    status_embed = discord.Embed(
        title=f"Verify your {symbol} holdings :money_with_wings: {LOADING_EMOJI}",
        description=f"Send **{amount} {symbol}** to:\n```\n{bot_wallet}\n```\nYour Wallet:\n```\n{wallet_address}\n```",
        color=discord.Color.blue()
    )
    status_embed.set_thumbnail(url="https://media.tenor.com/svjJfUlo3cgAAAAj/bino.gif")
    view = CopyAddressView()
    try:
        status_message = await interaction.followup.send(embed=status_embed, view=view)
        print(f"Sent verification embed to user {interaction.user.id}")
        pending_verifications[wallet_address] = (interaction, status_message, time.time())
        print(f"Added {wallet_address} to pending verifications")
    except Exception as e:
        print(f"Error sending verification embed: {e}")

@tree.command(name="checkwallets", description="Check verified wallets and update roles")
@app_commands.checks.has_permissions(manage_roles=True)
async def checkwallets(interaction: discord.Interaction):
    print(f"Checkwallets command triggered by user {interaction.user.id}")
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild.id)
    if guild_id not in bot_config or "token_address" not in bot_config[guild_id]:
        print(f"Token address not set for guild {guild_id}")
        await interaction.followup.send("Token address not set.", ephemeral=True)
        return
    contract = get_token_contract(bot_config[guild_id]["token_address"])
    decimals = bot_config[guild_id]["decimals"]
    symbol = bot_config[guild_id]["token_symbol"]
    guild = interaction.guild
    guild_thresholds = role_thresholds.get(guild_id, {})
    if not guild_thresholds:
        print(f"No role thresholds defined for guild {guild_id}")
        await interaction.followup.send("No role thresholds defined.", ephemeral=True)
        return
    updated = 0
    for wallet_addr, data in verified_wallets.get(guild_id, {}).items():
        try:
            print(f"Checking wallet {wallet_addr} for guild {guild_id}")
            current_balance = contract.functions.balanceOf(w3.to_checksum_address(wallet_addr)).call()
            print(f"Current balance of {wallet_addr}: {current_balance}")
            member = discord.utils.get(guild.members, name=data["username"].split("#")[0], discriminator=data["username"].split("#")[1])
            if not member:
                print(f"Member {data['username']} not found in guild {guild_id}")
                continue
            current_roles = [role_name for role_name, min_amount in guild_thresholds.items() if current_balance >= min_amount * (10 ** decimals)]
            member_roles = [role.name for role in member.roles if role.name in guild_thresholds]
            roles_added = []
            roles_removed = []
            for role_name in guild_thresholds:
                role = get(guild.roles, name=role_name)
                if not role:
                    print(f"Role {role_name} not found in guild {guild_id}")
                    continue
                if role_name in current_roles and role_name not in member_roles:
                    await member.add_roles(role)
                    roles_added.append(role_name)
                    print(f"Added role {role_name} to {member.id}")
                elif role_name not in current_roles and role_name in member_roles:
                    await member.remove_roles(role)
                    roles_removed.append(role_name)
                    print(f"Removed role {role_name} from {member.id}")
            verified_wallets[guild_id][wallet_addr].update({"balance": current_balance, "last_verified": time.time()})
            save_verified_wallets()
            updated += 1
            await send_log(
                guild_id,
                "Wallet Checked",
                f"Wallet: `{wallet_addr}`\nUsername: {data['username']}\nBalance: {current_balance / (10 ** decimals)} {symbol}\nAdded: {', '.join(roles_added) or 'None'}\nRemoved: {', '.join(roles_removed) or 'None'}",
                interaction.user
            )
        except Exception as e:
            print(f"Error checking wallet {wallet_addr}: {e}")
            await send_log(guild_id, "Check Error", f"Wallet `{wallet_addr}`: {e}", interaction.user)
    await interaction.followup.send(f"Updated {updated} wallets.", ephemeral=True)
    print(f"Completed checkwallets for {updated} wallets in guild {guild_id}")

@tree.command(name="newcheck", description="Add a role with a token threshold")
@app_commands.checks.has_permissions(manage_roles=True)
async def newcheck(interaction: discord.Interaction, role: str, minamount: int):
    guild_id = str(interaction.guild.id)
    print(f"Newcheck command triggered by user {interaction.user.id} for role {role} with threshold {minamount}")
    guild = interaction.guild
    discord_role = get(guild.roles, name=role) or await guild.create_role(name=role)
    role_thresholds.setdefault(guild_id, {})[role] = minamount
    save_role_thresholds()
    await interaction.response.send_message(f"Added role '{role}' with threshold {minamount}.", ephemeral=True)
    await send_log(guild_id, "Role Added", f"Role '{role}' with threshold {minamount}.", interaction.user)
    print(f"Added role {role} with threshold {minamount} in guild {guild_id}")

@tree.command(name="modifycheck", description="Modify a role threshold")
@app_commands.checks.has_permissions(manage_roles=True)
async def modifycheck(interaction: discord.Interaction, role: str, newamount: int):
    guild_id = str(interaction.guild.id)
    print(f"Modifycheck command triggered by user {interaction.user.id} for role {role} with new amount {newamount}")
    if guild_id not in role_thresholds or role not in role_thresholds[guild_id]:
        await interaction.response.send_message(f"Role '{role}' not found.", ephemeral=True)
        print(f"Role {role} not found in guild {guild_id}")
        return
    old_amount = role_thresholds[guild_id][role]
    role_thresholds[guild_id][role] = newamount
    save_role_thresholds()
    await interaction.response.send_message(f"Updated '{role}' to {newamount}.", ephemeral=True)
    await send_log(guild_id, "Role Modified", f"Updated '{role}' from {old_amount} to {newamount}.", interaction.user)
    print(f"Modified role {role} from {old_amount} to {newamount} in guild {guild_id}")

@tree.command(name="removecheck", description="Remove a role threshold")
@app_commands.checks.has_permissions(manage_roles=True)
async def removecheck(interaction: discord.Interaction, role: str):
    guild_id = str(interaction.guild.id)
    print(f"Removecheck command triggered by user {interaction.user.id} for role {role}")
    if guild_id not in role_thresholds or role not in role_thresholds[guild_id]:
        await interaction.response.send_message(f"Role '{role}' not found.", ephemeral=True)
        print(f"Role {role} not found in guild {guild_id}")
        return
    del role_thresholds[guild_id][role]
    if not role_thresholds[guild_id]:
        del role_thresholds[guild_id]
    save_role_thresholds()
    await interaction.response.send_message(f"Removed '{role}'.", ephemeral=True)
    await send_log(guild_id, "Role Removed", f"Removed '{role}'.", interaction.user)
    print(f"Removed role {role} from guild {guild_id}")


@bot.event
async def on_ready():
    await tree.sync()
    print(f"{Back.LIGHTGREEN_EX}   LOG   {Back.RESET} Bot ready and commands synced.")
    guild_id = str(YOUR_GUILD_ID)
    if guild_id not in role_thresholds:
        role_thresholds[guild_id] = {"verified": 0, "HODLer": 1000000, "Moonwalker": 10000001}
        save_role_thresholds()
        print(f"Initialized default role thresholds for guild {guild_id}")
    bot.loop.create_task(monitor_transactions())
    bot.loop.create_task(check_timeouts())
    for guild_id in bot_config:
        await send_log(guild_id, "Bot Started", "Bot has started.")
    print(f"{Back.LIGHTGREEN_EX}   LOG   {Back.RESET} Background tasks started")



bot.run("MTM1MTk5MjU4MjU2OTMzMjc0Ng.GeKOeJ.BqRbVjBlvMfSAZQZJQgTLXWlqpsKDrXLF0SvE4")