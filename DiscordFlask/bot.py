import os
import logging
import discord
from discord.ext import commands
from app import app
from models import Staff, GameBan
from admin_manager import add_admin, delete_admin, check_admin, add_log

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    logging.info(f'{bot.user} has connected to Discord!')
    logging.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Set bot status
    activity = discord.Game(name="Monitorando bans do jogo")
    await bot.change_presence(activity=activity)

@bot.command(name='checkban')
async def check_ban(ctx, player_id: str = None):
    """Check if a game player is banned"""
    if player_id is None:
        await ctx.send("❌ Por favor forneça um ID de jogador. Uso: `!checkban <player_id>`")
        return
    
    try:
        with app.app_context():
            ban = GameBan.query.filter_by(player_id=str(player_id), is_active=True).first()
            
            if ban and not ban.is_expired():
                embed = discord.Embed(
                    title="🚫 Jogador Banido",
                    color=discord.Color.red(),
                    description=f"**ID do Jogador:** {player_id}"
                )
                
                if ban.player_name:
                    embed.add_field(name="Nome", value=ban.player_name, inline=True)
                
                embed.add_field(name="Motivo", value=ban.reason, inline=False)
                embed.add_field(name="Tipo", value="Permanente" if ban.ban_type == 'permanent' else "Temporário", inline=True)
                embed.add_field(name="Banido por", value=ban.staff_member.username, inline=True)
                embed.add_field(name="Data", value=ban.created_at.strftime('%d/%m/%Y %H:%M'), inline=True)
                
                if ban.ban_type == 'temporary' and ban.expires_at:
                    embed.add_field(name="Expira em", value=ban.expires_at.strftime('%d/%m/%Y %H:%M'), inline=True)
                    remaining = ban.time_remaining()
                    if remaining:
                        embed.add_field(name="Tempo restante", value=str(remaining).split('.')[0], inline=True)
                
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="✅ Jogador Liberado",
                    color=discord.Color.green(),
                    description=f"**ID do Jogador:** {player_id}\n\nEste jogador não está banido."
                )
                await ctx.send(embed=embed)
            
    except Exception as e:
        logging.error(f"Error checking ban for {player_id}: {e}")
        await ctx.send(f"❌ Erro ao verificar ban: {str(e)}")

@bot.command(name='banlist')
async def ban_list(ctx, page: int = 1):
    """Show list of banned players"""
    try:
        with app.app_context():
            # Get active bans
            all_bans = GameBan.query.filter_by(is_active=True).order_by(GameBan.created_at.desc()).all()
            active_bans = [ban for ban in all_bans if not ban.is_expired()]
            
            if not active_bans:
                embed = discord.Embed(
                    title="📋 Lista de Bans",
                    color=discord.Color.blue(),
                    description="Não há jogadores banidos no momento."
                )
                await ctx.send(embed=embed)
                return
            
            # Pagination
            items_per_page = 5
            total_pages = (len(active_bans) + items_per_page - 1) // items_per_page
            page = max(1, min(page, total_pages))
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_bans = active_bans[start_idx:end_idx]
            
            # Create embed
            embed = discord.Embed(
                title="📋 Lista de Jogadores Banidos",
                color=discord.Color.orange(),
                description=f"**Total de bans ativos:** {len(active_bans)}\n**Página {page} de {total_pages}**"
            )
            
            for ban in page_bans:
                ban_info = f"**Motivo:** {ban.reason[:100]}{'...' if len(ban.reason) > 100 else ''}"
                ban_info += f"\n**Tipo:** {'Permanente' if ban.ban_type == 'permanent' else 'Temporário'}"
                ban_info += f"\n**Por:** {ban.staff_member.username}"
                ban_info += f"\n**Data:** {ban.created_at.strftime('%d/%m/%Y')}"
                
                if ban.ban_type == 'temporary' and ban.expires_at:
                    remaining = ban.time_remaining()
                    if remaining:
                        ban_info += f"\n**Expira em:** {str(remaining).split('.')[0]}"
                
                player_title = f"{ban.player_id}"
                if ban.player_name:
                    player_title += f" ({ban.player_name})"
                
                embed.add_field(
                    name=player_title,
                    value=ban_info,
                    inline=False
                )
            
            if total_pages > 1:
                embed.set_footer(text=f"Use !banlist {page + 1} para ver a próxima página" if page < total_pages else "Esta é a última página")
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        logging.error(f"Error getting ban list: {e}")
        await ctx.send(f"❌ Erro ao obter lista de bans: {str(e)}")

@bot.command(name='banstats')
async def ban_stats(ctx):
    """Show ban statistics"""
    try:
        with app.app_context():
            all_bans = GameBan.query.filter_by(is_active=True).all()
            active_bans = [ban for ban in all_bans if not ban.is_expired()]
            permanent_bans = [ban for ban in active_bans if ban.ban_type == 'permanent']
            temporary_bans = [ban for ban in active_bans if ban.ban_type == 'temporary']
            
            embed = discord.Embed(
                title="📊 Estatísticas de Bans",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Total de Bans", value=str(len(all_bans)), inline=True)
            embed.add_field(name="Bans Ativos", value=str(len(active_bans)), inline=True)
            embed.add_field(name="Bans Permanentes", value=str(len(permanent_bans)), inline=True)
            embed.add_field(name="Bans Temporários", value=str(len(temporary_bans)), inline=True)
            
            if active_bans:
                # Count by staff member
                staff_counts = {}
                for ban in active_bans:
                    staff_name = ban.staff_member.username
                    staff_counts[staff_name] = staff_counts.get(staff_name, 0) + 1
                
                # Get most active staff
                if staff_counts:
                    top_staff = max(staff_counts.items(), key=lambda x: x[1])
                    embed.add_field(name="Staff Mais Ativo", value=f"{top_staff[0]} ({top_staff[1]} bans)", inline=True)
            
            embed.add_field(name="Status do Bot", value="🟢 Online", inline=True)
            embed.add_field(name="Servidor do Jogo", value="🎮 Monitorando", inline=True)
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        logging.error(f"Error getting ban stats: {e}")
        await ctx.send(f"❌ Erro ao obter estatísticas: {str(e)}")

@bot.command(name='search')
async def search_player(ctx, *, search_term: str = None):
    """Search for a player by ID or name"""
    if search_term is None:
        await ctx.send("❌ Por favor forneça um termo de busca. Uso: `!search <id_ou_nome>`")
        return
    
    try:
        with app.app_context():
            # Search by player ID or name
            bans = GameBan.query.filter(
                GameBan.is_active == True,
                (GameBan.player_id.ilike(f'%{search_term}%') | 
                 GameBan.player_name.ilike(f'%{search_term}%'))
            ).order_by(GameBan.created_at.desc()).limit(5).all()
            
            if not bans:
                embed = discord.Embed(
                    title="🔍 Busca de Jogadores",
                    color=discord.Color.yellow(),
                    description=f"Nenhum resultado encontrado para: **{search_term}**"
                )
                await ctx.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🔍 Resultados da Busca",
                color=discord.Color.blue(),
                description=f"**Termo buscado:** {search_term}\n**Resultados encontrados:** {len(bans)}"
            )
            
            for ban in bans:
                status = "Ativo" if not ban.is_expired() else "Expirado"
                player_title = f"{ban.player_id}"
                if ban.player_name:
                    player_title += f" ({ban.player_name})"
                
                ban_info = f"**Status:** {status}\n**Motivo:** {ban.reason[:100]}{'...' if len(ban.reason) > 100 else ''}"
                ban_info += f"\n**Tipo:** {'Permanente' if ban.ban_type == 'permanent' else 'Temporário'}"
                ban_info += f"\n**Data:** {ban.created_at.strftime('%d/%m/%Y')}"
                
                embed.add_field(
                    name=player_title,
                    value=ban_info,
                    inline=False
                )
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        logging.error(f"Error searching for player {search_term}: {e}")
        await ctx.send(f"❌ Erro na busca: {str(e)}")

@bot.command(name='addadmin')
async def add_admin_command(ctx, username: str, password: str):
    """Cria um novo admin (apenas para superadmins já no arquivo)."""
    # Verifica se o autor do comando é um admin
    author_name = str(ctx.author)
    
    if add_admin(username, password):
        add_log("AddAdmin (Discord)", username, author_name)
        await ctx.send(f"✅ Admin `{username}` criado com sucesso!")
    else:
        await ctx.send(f"⚠ O admin `{username}` já existe.")

@bot.command(name='deladmin')
async def delete_admin_command(ctx, username: str):
    """Deleta um admin existente."""
    author_name = str(ctx.author)
    
    if delete_admin(username):
        add_log("DelAdmin (Discord)", username, author_name)
        await ctx.send(f"🗑 Admin `{username}` foi removido!")
    else:
        await ctx.send(f"⚠ O admin `{username}` não existe.")

@bot.command(name='listadmins')
async def list_admins_command(ctx):
    """Lista todos os administradores."""
    try:
        from admin_manager import load_admins
        admins = load_admins()
        
        if not admins:
            embed = discord.Embed(
                title="👥 Lista de Administradores",
                color=discord.Color.blue(),
                description="Nenhum administrador encontrado."
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="👥 Lista de Administradores",
            color=discord.Color.blue(),
            description=f"**Total:** {len(admins)} administradores"
        )
        
        admin_list = "\n".join([f"• {admin['username']}" for admin in admins])
        embed.add_field(
            name="Administradores",
            value=admin_list,
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logging.error(f"Error listing admins: {e}")
        await ctx.send(f"❌ Erro ao listar administradores: {str(e)}")

@bot.command(name='help_game')
async def help_game(ctx):
    """Show help for game ban commands"""
    embed = discord.Embed(
        title="🎮 Comandos do Bot de Bans",
        color=discord.Color.blue(),
        description="Comandos disponíveis para verificação de bans do jogo"
    )
    
    embed.add_field(
        name="📋 Comandos de Bans",
        value="`!checkban <player_id>` - Verifica se jogador está banido\n"
              "`!banlist [página]` - Lista jogadores banidos\n"
              "`!search <termo>` - Busca jogadores\n"
              "`!banstats` - Estatísticas de bans",
        inline=False
    )
    
    embed.add_field(
        name="👥 Comandos de Admin",
        value="`!addadmin <user> <pass>` - Adiciona admin\n"
              "`!deladmin <user>` - Remove admin\n"
              "`!listadmins` - Lista todos os admins",
        inline=False
    )
    
    embed.add_field(
        name="🌐 Painel Web",
        value="Use o painel web para gerenciar bans e admins",
        inline=False
    )
    
    embed.set_footer(text="Bot de Monitoramento de Bans do Jogo")
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento obrigatório faltando. Use `!help_game` para ajuda.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Argumento inválido. Use `!help_game` para ajuda.")
    else:
        logging.error(f"Command error: {error}")
        await ctx.send(f"❌ Ocorreu um erro: {str(error)}")

def run_bot():
    """Run the Discord bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logging.warning("DISCORD_BOT_TOKEN environment variable not found! Bot will not start.")
        return
    
    try:
        bot.run(token)
    except Exception as e:
        logging.error(f"Error running bot: {e}")