from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Import db from app - this will be resolved when app imports this module
from app import db


class Staff(UserMixin, db.Model):
    """Staff users who can manage game bans"""
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship with bans
    bans_created = db.relationship('GameBan', backref='staff_member', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Staff {self.username}>'


class GameBan(db.Model):
    """Game player bans"""
    __tablename__ = 'game_bans'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.String(100), nullable=False, index=True)  # Game player ID
    player_name = db.Column(db.String(100), nullable=True)  # Player display name
    reason = db.Column(db.Text, nullable=False)
    ban_type = db.Column(db.String(50), default='permanent')  # permanent, temporary
    expires_at = db.Column(db.DateTime, nullable=True)  # For temporary bans
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Foreign key to staff member who created the ban
    banned_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    
    def is_expired(self):
        """Check if temporary ban has expired"""
        if self.ban_type == 'temporary' and self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def time_remaining(self):
        """Get remaining time for temporary bans"""
        if self.ban_type == 'temporary' and self.expires_at and not self.is_expired():
            return self.expires_at - datetime.now()
        return None
    
    def __repr__(self):
        return f'<GameBan {self.player_id}: {self.reason[:50]}>'