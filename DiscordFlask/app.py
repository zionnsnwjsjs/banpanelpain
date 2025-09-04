import os
import logging
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta

class Base(DeclarativeBase):
    pass

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set!")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db = SQLAlchemy(model_class=Base)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Você precisa fazer login para acessar esta página.'
login_manager.login_message_category = 'warning'

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401

    db.create_all()
    
    # Create default admin if no staff exists
    from models import Staff
    if not Staff.query.first():
        admin = Staff(
            username='admin',
            email='admin@game.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logging.info('Created default admin user (admin/admin123)')

@login_manager.user_loader
def load_user(user_id):
    # Import locally to avoid circular import
    from admin_manager import load_admins
    from models import Staff
    
    # Primeiro tenta carregar do arquivo JSON
    admins = load_admins()
    for admin in admins:
        if admin["username"] == user_id:
            class MockUser:
                def __init__(self, username):
                    self.id = username
                    self.username = username
                    self.is_admin = True
                    self.is_active = True
                    
                def is_authenticated(self):
                    return True
                    
                def is_anonymous(self):
                    return False
                    
                def get_id(self):
                    return self.id
            return MockUser(user_id)
    
    # Se não encontrou no JSON, tenta no banco de dados
    try:
        return Staff.query.get(int(user_id))
    except (ValueError, TypeError):
        return None


# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Staff login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Import locally to avoid circular import
        from admin_manager import check_admin
        from models import Staff
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Usuario e senha são obrigatórios', 'error')
            return render_template('login.html')
        
        # Primeiro verifica o arquivo JSON de admins
        if check_admin(username, password):
            # Create a mock user object for Flask-Login
            class MockUser:
                def __init__(self, username):
                    self.id = username
                    self.username = username
                    self.is_admin = True
                    self.is_active = True
                    
                def is_authenticated(self):
                    return True
                    
                def is_anonymous(self):
                    return False
                    
                def get_id(self):
                    return self.id
            
            user = MockUser(username)
            login_user(user, remember=True)
            flash(f'Bem-vindo, {username}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        
        # Se não encontrou no JSON, verifica no banco de dados
        staff = Staff.query.filter_by(username=username).first()
        
        if staff and staff.check_password(password) and staff.is_active:
            login_user(staff, remember=True)
            flash(f'Bem-vindo, {staff.username}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Staff logout"""
    username = current_user.username
    logout_user()
    flash(f'Logout realizado com sucesso. Até logo, {username}!', 'info')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
def index():
    """Main page with game ban management interface"""
    from models import GameBan
    bans = GameBan.query.filter_by(is_active=True).order_by(GameBan.created_at.desc()).all()
    total_bans = len(bans)
    active_bans = len([b for b in bans if not b.is_expired()])
    return render_template('index.html', bans=bans, total_bans=total_bans, active_bans=active_bans)

# API routes for ban management
@app.route('/api/bans', methods=['GET'])
@login_required
def api_get_bans():
    """API endpoint to get all active bans"""
    from models import GameBan
    try:
        bans = GameBan.query.filter_by(is_active=True).order_by(GameBan.created_at.desc()).all()
        ban_list = []
        
        for ban in bans:
            ban_data = {
                'id': ban.id,
                'player_id': ban.player_id,
                'player_name': ban.player_name,
                'reason': ban.reason,
                'ban_type': ban.ban_type,
                'is_expired': ban.is_expired(),
                'created_at': ban.created_at.isoformat(),
                'banned_by': ban.staff_member.username
            }
            
            if ban.ban_type == 'temporary' and ban.expires_at:
                ban_data['expires_at'] = ban.expires_at.isoformat()
                remaining = ban.time_remaining()
                if remaining:
                    ban_data['time_remaining'] = str(remaining)
            
            ban_list.append(ban_data)
        
        return jsonify({
            'success': True,
            'bans': ban_list,
            'total': len(ban_list)
        })
    except Exception as e:
        logging.error(f"Error getting bans: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bans', methods=['POST'])
@login_required
def api_add_ban():
    """API endpoint to add a game ban"""
    from models import GameBan, Staff
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados JSON não fornecidos'
            }), 400
        
        player_id = data.get('player_id')
        player_name = data.get('player_name', '')
        reason = data.get('reason', 'Nenhum motivo fornecido')
        ban_type = data.get('ban_type', 'permanent')
        expires_in_hours = data.get('expires_in_hours')
        
        if not player_id:
            return jsonify({
                'success': False,
                'error': 'ID do jogador é obrigatório'
            }), 400
        
        # Check if player is already banned
        existing_ban = GameBan.query.filter_by(player_id=str(player_id), is_active=True).first()
        if existing_ban and not existing_ban.is_expired():
            return jsonify({
                'success': False,
                'error': 'Jogador já está banido'
            }), 409
        
        # Calculate expiration for temporary bans
        expires_at = None
        if ban_type == 'temporary' and expires_in_hours:
            try:
                expires_at = datetime.now() + timedelta(hours=int(expires_in_hours))
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Tempo de expiração inválido'
                }), 400
        
        # Get banned_by_id (handle both JSON admin and DB staff)
        banned_by_id = None
        if hasattr(current_user, 'id') and isinstance(current_user.id, int):
            banned_by_id = current_user.id
        else:
            # For JSON admins, find or create a staff record
            staff = Staff.query.filter_by(username=current_user.username).first()
            if not staff:
                staff = Staff(
                    username=current_user.username,
                    email=f"{current_user.username}@admin.local",
                    is_admin=True
                )
                staff.set_password('temp_password')
                db.session.add(staff)
                db.session.commit()
            banned_by_id = staff.id
        
        # Create new ban
        new_ban = GameBan(
            player_id=str(player_id),
            player_name=player_name,
            reason=reason,
            ban_type=ban_type,
            expires_at=expires_at,
            banned_by_id=banned_by_id
        )
        
        db.session.add(new_ban)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Jogador {player_id} foi banido com sucesso',
            'ban_id': new_ban.id
        })
            
    except Exception as e:
        logging.error(f"Error adding ban: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bans/<int:ban_id>', methods=['DELETE'])
@login_required
def api_remove_ban(ban_id):
    """API endpoint to remove a ban"""
    from models import GameBan
    try:
        ban = GameBan.query.get_or_404(ban_id)
        
        ban.is_active = False
        ban.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Ban do jogador {ban.player_id} foi removido'
        })
            
    except Exception as e:
        logging.error(f"Error removing ban: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bans/check/<player_id>', methods=['GET'])
@login_required
def api_check_ban(player_id):
    """API endpoint to check if a player is banned"""
    from models import GameBan
    try:
        ban = GameBan.query.filter_by(player_id=str(player_id), is_active=True).first()
        
        is_banned = ban is not None and not ban.is_expired()
        
        result = {
            'success': True,
            'player_id': player_id,
            'is_banned': is_banned,
            'ban_info': None
        }
        
        if is_banned:
            result['ban_info'] = {
                'id': ban.id,
                'reason': ban.reason,
                'ban_type': ban.ban_type,
                'created_at': ban.created_at.isoformat(),
                'banned_by': ban.staff_member.username
            }
            
            if ban.ban_type == 'temporary' and ban.expires_at:
                result['ban_info']['expires_at'] = ban.expires_at.isoformat()
                remaining = ban.time_remaining()
                if remaining:
                    result['ban_info']['time_remaining'] = str(remaining)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error checking ban: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Web form routes
@app.route('/add_ban', methods=['POST'])
@login_required
def web_add_ban():
    """Web form endpoint to add a ban"""
    from models import GameBan, Staff
    try:
        player_id = request.form.get('player_id')
        player_name = request.form.get('player_name', '')
        reason = request.form.get('reason', 'Nenhum motivo fornecido')
        ban_type = request.form.get('ban_type', 'permanent')
        expires_in_hours = request.form.get('expires_in_hours')
        
        if not player_id:
            flash('ID do jogador é obrigatório', 'error')
            return redirect(url_for('index'))
        
        # Check if player is already banned
        existing_ban = GameBan.query.filter_by(player_id=str(player_id), is_active=True).first()
        if existing_ban and not existing_ban.is_expired():
            flash(f'Jogador {player_id} já está banido', 'warning')
            return redirect(url_for('index'))
        
        # Calculate expiration for temporary bans
        expires_at = None
        if ban_type == 'temporary' and expires_in_hours:
            try:
                expires_at = datetime.now() + timedelta(hours=int(expires_in_hours))
            except (ValueError, TypeError):
                flash('Tempo de expiração inválido', 'error')
                return redirect(url_for('index'))
        
        # Get banned_by_id (handle both JSON admin and DB staff)
        banned_by_id = None
        if hasattr(current_user, 'id') and isinstance(current_user.id, int):
            banned_by_id = current_user.id
        else:
            # For JSON admins, find or create a staff record
            staff = Staff.query.filter_by(username=current_user.username).first()
            if not staff:
                staff = Staff(
                    username=current_user.username,
                    email=f"{current_user.username}@admin.local",
                    is_admin=True
                )
                staff.set_password('temp_password')
                db.session.add(staff)
                db.session.commit()
            banned_by_id = staff.id
        
        # Create new ban
        new_ban = GameBan(
            player_id=str(player_id),
            player_name=player_name,
            reason=reason,
            ban_type=ban_type,
            expires_at=expires_at,
            banned_by_id=banned_by_id
        )
        
        db.session.add(new_ban)
        db.session.commit()
        
        ban_msg = f'Jogador {player_id} foi banido'
        if ban_type == 'temporary' and expires_at:
            ban_msg += f' por {expires_in_hours} horas'
        flash(ban_msg, 'success')
            
    except Exception as e:
        logging.error(f"Error adding ban via web: {e}")
        db.session.rollback()
        flash(f'Erro ao banir jogador: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/remove_ban/<int:ban_id>', methods=['POST'])
@login_required
def web_remove_ban(ban_id):
    """Web endpoint to remove a ban"""
    from models import GameBan
    try:
        ban = GameBan.query.get_or_404(ban_id)
        
        ban.is_active = False
        ban.updated_at = datetime.now()
        db.session.commit()
        
        flash(f'Ban do jogador {ban.player_id} foi removido', 'success')
            
    except Exception as e:
        logging.error(f"Error removing ban via web: {e}")
        db.session.rollback()
        flash(f'Erro ao remover ban: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# Admin management routes
@app.route('/admin_panel')
@login_required
def admin_panel():
    """Admin panel for managing admins and staff"""
    from admin_manager import list_admins, get_logs
    from models import Staff
    
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem ver esta página.', 'error')
        return redirect(url_for('index'))
    
    # Get JSON admins, DB staff and logs
    json_admins = list_admins()
    staff_members = Staff.query.order_by(Staff.created_at.desc()).all()
    recent_logs = get_logs(20)  # Get last 20 logs
    
    return render_template('admin_panel.html', json_admins=json_admins, staff_members=staff_members, recent_logs=recent_logs)

@app.route('/add_json_admin', methods=['POST'])
@login_required
def add_json_admin():
    """Add a new JSON admin"""
    from admin_manager import add_admin
    
    if not current_user.is_admin:
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Usuário e senha são obrigatórios', 'error')
        return redirect(url_for('admin_panel'))
    
    if add_admin(username, password, current_user.username):
        flash(f'Admin {username} adicionado com sucesso', 'success')
    else:
        flash(f'Admin {username} já existe', 'warning')
    
    return redirect(url_for('admin_panel'))

@app.route('/delete_json_admin/<username>', methods=['POST'])
@login_required
def delete_json_admin(username):
    """Delete a JSON admin"""
    from admin_manager import delete_admin
    
    if not current_user.is_admin:
        flash('Acesso negado.', 'error')
        return redirect(url_for('index'))
    
    if username == current_user.username:
        flash('Você não pode deletar a si mesmo', 'error')
        return redirect(url_for('admin_panel'))
    
    if delete_admin(username, current_user.username):
        flash(f'Admin {username} removido com sucesso', 'success')
    else:
        flash(f'Admin {username} não encontrado', 'error')
    
    return redirect(url_for('admin_panel'))

# Legacy staff route for compatibility
@app.route('/staff')
@login_required
def staff_list():
    """Redirect to admin panel"""
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)