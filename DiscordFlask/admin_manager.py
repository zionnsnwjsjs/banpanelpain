import os
import json
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

ADMIN_FILE = "admins.json"

# Cria o arquivo se não existir
if not os.path.exists(ADMIN_FILE):
    with open(ADMIN_FILE, "w") as f:
        json.dump([{"username": "zion", "password": "zionbest"}], f)

def load_admins():
    """Carrega a lista de administradores do arquivo JSON"""
    try:
        with open(ADMIN_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar admins: {e}")
        return []

def save_admins(admins):
    """Salva a lista de administradores no arquivo JSON"""
    try:
        with open(ADMIN_FILE, "w") as f:
            json.dump(admins, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar admins: {e}")
        return False

def check_admin(username, password):
    """Verifica se o usuário e senha são válidos"""
    admins = load_admins()
    for adm in admins:
        if adm["username"] == username and adm["password"] == password:
            return True
    return False

def add_admin(username, password, author="System"):
    """Adiciona um novo administrador"""
    admins = load_admins()
    if any(a["username"] == username for a in admins):
        return False  # já existe
    admins.append({"username": username, "password": password})
    success = save_admins(admins)
    if success:
        add_log("AddAdmin (Web)", username, author)
    return success

def delete_admin(username, author="System"):
    """Remove um administrador"""
    admins = load_admins()
    new_admins = [a for a in admins if a["username"] != username]
    if len(new_admins) == len(admins):
        return False  # não existe
    success = save_admins(new_admins)
    if success:
        add_log("DelAdmin (Web)", username, author)
    return success

def list_admins():
    """Lista todos os administradores (sem mostrar senhas)"""
    admins = load_admins()
    return [{"username": a["username"]} for a in admins]

def update_admin_password(username, new_password):
    """Atualiza a senha de um administrador"""
    admins = load_admins()
    for adm in admins:
        if adm["username"] == username:
            adm["password"] = new_password
            return save_admins(admins)
    return False

def get_admin_count():
    """Retorna o número total de administradores"""
    return len(load_admins())

def add_log(action, target, author="System"):
    """Adiciona um log de ação administrativa"""
    log_file = "admin_logs.json"
    
    # Carrega logs existentes ou cria lista vazia
    if os.path.exists(log_file):
        try:
            with open(log_file, "r") as f:
                logs = json.load(f)
        except:
            logs = []
    else:
        logs = []
    
    # Adiciona novo log
    new_log = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "target": target,
        "author": author
    }
    
    logs.append(new_log)
    
    # Mantém apenas os últimos 100 logs
    if len(logs) > 100:
        logs = logs[-100:]
    
    # Salva logs
    try:
        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
        logging.info(f"Log adicionado: {action} - {target} por {author}")
    except Exception as e:
        logging.error(f"Erro ao salvar log: {e}")

def get_logs(limit=50):
    """Retorna os logs mais recentes"""
    log_file = "admin_logs.json"
    
    if not os.path.exists(log_file):
        return []
    
    try:
        with open(log_file, "r") as f:
            logs = json.load(f)
        return logs[-limit:] if len(logs) > limit else logs
    except Exception as e:
        logging.error(f"Erro ao carregar logs: {e}")
        return []