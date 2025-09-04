# Sistema de Banimento de Jogo

## Overview

This is a game player ban management system that provides both a web interface and Discord bot functionality for managing player bans. The application uses a dual-interface approach with a Flask web application for staff administrative management and a Discord bot for real-time ban checking within Discord servers. The system includes staff authentication and role-based access control.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Application Structure
The system follows a modular architecture with clear separation of concerns:

- **Flask Web Application** (`app.py`): Provides a web-based interface for staff login and game ban management with both HTML pages and REST API endpoints
- **Discord Bot** (`bot.py`): Handles Discord-specific commands and interactions for ban checking and management within Discord servers
- **Database Models** (`models.py`): SQLAlchemy models for Staff users and GameBan records with PostgreSQL storage
- **Main Entry Point** (`main.py`): Orchestrates both Flask and Discord bot services using threading

### Data Storage Strategy
The application uses PostgreSQL database for robust data management:
- **Staff Authentication** with secure password hashing using Werkzeug
- **Game Ban Records** with player ID, reason, ban type (permanent/temporary), expiration dates
- **Role-based Access Control** with admin and regular staff permissions
- **Relationship Management** linking bans to staff members who created them

### Frontend Architecture
- **Staff Authentication System** with login/logout functionality
- **Server-side rendered** HTML templates using Jinja2 with role-based content
- **Bootstrap dark theme** with game-focused styling and Portuguese language support
- **Progressive enhancement** with JavaScript for dynamic interactions and real-time updates
- **REST API endpoints** for game integration and programmatic access to ban data

### Bot Integration
- **Discord.py framework** for bot functionality
- **Game-focused commands** (!checkban, !banlist, !search, !banstats, !help_game)
- **Rich embed responses** with game context and Portuguese language support
- **Player search functionality** by ID or name with pagination
- **Real-time ban status checking** with temporary ban time remaining display

### Security Considerations
- **Staff Authentication** with Flask-Login and secure password storage
- **Role-based Authorization** protecting admin functions and sensitive operations
- **Environment-based configuration** for sensitive data (session secrets, bot tokens, database credentials)
- **Input validation** on both web and bot interfaces with CSRF protection
- **Database Security** with PostgreSQL and SQLAlchemy ORM preventing SQL injection

## External Dependencies

### Core Frameworks
- **Flask**: Web framework with Flask-Login for staff authentication and session management
- **SQLAlchemy**: ORM for database operations with PostgreSQL
- **Discord.py**: Python library for Discord bot development and API interaction

### Frontend Libraries
- **Bootstrap 5**: UI framework with Replit dark theme for consistent styling
- **Font Awesome**: Icon library for enhanced user interface elements
- **JavaScript**: Enhanced interactivity with search, export, and real-time updates

### Python Libraries
- **Flask-Login**: User session management and authentication
- **Werkzeug**: Password hashing and security utilities
- **Threading**: Built-in library for concurrent execution of Flask and Discord bot
- **Logging**: Built-in library for application monitoring and debugging

### Runtime Environment
- **PostgreSQL Database**: DATABASE_URL and related environment variables
- **Discord Bot Token**: Required environment variable for bot authentication
- **Session Secret**: Environment variable for Flask session security

The architecture prioritizes security and scalability while providing robust functionality for managing game player bans through authenticated web interface and Discord bot integration. The system supports both permanent and temporary bans with automatic expiration handling.