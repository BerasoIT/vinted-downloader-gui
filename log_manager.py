#!/usr/bin/env python3
"""
Log Manager per Vinted Downloader GUI
Gestisce i log in modo intelligente e user-friendly
"""

import logging
import os
import sys
from pathlib import Path


class LogManager:
    """Gestisce i log in modo semplice e centralizzato"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.debug_mode = self._detect_debug_mode()
            self.file_logging_enabled = False
            self.loggers = {}
            LogManager._initialized = True
    
    def _detect_debug_mode(self):
        """Rileva se l'applicazione è stata avviata dal debugger di VS Code"""
        return (hasattr(sys, 'gettrace') and sys.gettrace() is not None) or \
               ('debugpy' in sys.modules) or \
               os.getenv('VSCODE_DEBUG', '0') == '1' or \
               '--debug' in sys.argv
    
    def enable_file_logging(self, enabled=True):
        """Abilita/disabilita il logging su file"""
        self.file_logging_enabled = enabled
        self._reconfigure_all_loggers()
    
    def get_logger(self, name):
        """Ottiene un logger configurato correttamente"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self._configure_logger(logger)
            self.loggers[name] = logger
        return self.loggers[name]
    
    def _configure_logger(self, logger):
        """Configura un singolo logger"""
        # Rimuovi tutti i handler esistenti per evitare duplicati
        logger.handlers.clear()
        
        if self.debug_mode or self.file_logging_enabled:
            logger.setLevel(logging.DEBUG)
            
            # Handler per console (solo in modalità debug VS Code)
            if self.debug_mode:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
                logger.addHandler(console_handler)
            
            # Handler per file (solo se abilitato)
            if self.file_logging_enabled:
                file_handler = logging.FileHandler('debug_gui.log', mode='a', encoding='utf-8')
                file_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                )
                logger.addHandler(file_handler)
        else:
            # Modalità produzione: nessun logging
            logger.setLevel(logging.CRITICAL)
        
        # Evita la propagazione per prevenire duplicati
        logger.propagate = False
    
    def _reconfigure_all_loggers(self):
        """Riconfigura tutti i logger esistenti"""
        for logger in self.loggers.values():
            self._configure_logger(logger)
    
    def is_debug_mode(self):
        """Restituisce True se siamo in modalità debug"""
        return self.debug_mode
    
    def is_file_logging_enabled(self):
        """Restituisce True se il logging su file è abilitato"""
        return self.file_logging_enabled


# Istanza globale del manager
log_manager = LogManager()


def get_logger(name):
    """Funzione di convenienza per ottenere un logger configurato"""
    return log_manager.get_logger(name)


def enable_file_logging(enabled=True):
    """Funzione di convenienza per abilitare/disabilitare il logging su file"""
    log_manager.enable_file_logging(enabled)


def is_debug_mode():
    """Funzione di convenienza per verificare la modalità debug"""
    return log_manager.is_debug_mode()


def is_file_logging_enabled():
    """Funzione di convenienza per verificare se il logging su file è abilitato"""
    return log_manager.is_file_logging_enabled()
