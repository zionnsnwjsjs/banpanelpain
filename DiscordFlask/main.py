import threading
import logging
from app import app
from bot import run_bot

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def run_flask():
    """Run the Flask application"""
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

def run_discord_bot():
    """Run the Discord bot"""
    run_bot()

if __name__ == '__main__':
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app in main thread
    run_flask()
