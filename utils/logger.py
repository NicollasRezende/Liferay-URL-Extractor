# -*- coding: utf-8 -*-
"""
Módulo de logging para Liferay URL Extractor

Este módulo fornece facilidades para logging consistente através da aplicação,
utilizando o pacote Rich para formatação e cores.

Uso:
    from utils.logger import Logger
    logger = Logger(console)
    logger.info("Mensagem informativa")
    logger.error("Mensagem de erro")
"""

import datetime
from rich.console import Console
from rich.text import Text
from dataclasses import dataclass

class Logger:
    """Gerenciador de logs com formatação Rich."""
    
    # Definição de cores para os diferentes níveis de log
    LOG_COLORS = {
        "INFO": "green",
        "DEBUG": "blue",
        "WARN": "yellow",
        "ERROR": "red bold",
        "SUCCESS": "green bold",
        "CACHE": "magenta"
    }
    
    def __init__(self, console: Console):
        """
        Inicializa o logger.
        
        Args:
            console: Instância de Rich Console para output
        """
        self.console = console
    
    def log(self, level: str, message: str):
        """
        Registra uma mensagem de log com nível e timestamp.
        
        Args:
            level: Nível do log (INFO, DEBUG, ERROR, etc.)
            message: Mensagem a ser registrada
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        level_text = Text(f"[{level}]", style=self.LOG_COLORS.get(level, "white"))
        time_text = Text(f"[{timestamp}]", style="bright_black")
        self.console.print(f"{time_text} {level_text} {message}")
    
    def info(self, message: str):
        """Registra uma mensagem informativa."""
        self.log("INFO", message)
    
    def debug(self, message: str):
        """Registra uma mensagem de debug."""
        self.log("DEBUG", message)
    
    def warn(self, message: str):
        """Registra uma mensagem de aviso."""
        self.log("WARN", message)
    
    def error(self, message: str):
        """Registra uma mensagem de erro."""
        self.log("ERROR", message)
    
    def success(self, message: str):
        """Registra uma mensagem de sucesso."""
        self.log("SUCCESS", message)
    
    def cache(self, message: str):
        """Registra uma mensagem relacionada ao cache."""
        self.log("CACHE", message)
    
    def display_config(self, config):
        """
        Exibe as configurações do aplicativo de forma formatada.
        
        Args:
            config: Objeto de configuração do aplicativo
        """
        self.console.print(f"\n[cyan]Configurações:[/cyan]")
        self.console.print(f"  URL Base: [yellow]{config.LIFERAY_URL}[/yellow]")
        self.console.print(f"  Grupo ID: [yellow]{config.GROUP_ID}[/yellow]")
        self.console.print(f"  Requisições Paralelas: [yellow]{config.MAX_CONCURRENT_REQUESTS}[/yellow]")
        self.console.print(f"  Cache: [yellow]{'Ativado (' + str(config.CACHE_TTL) + 'h)' if config.CACHE_TTL > 0 else 'Desativado'}[/yellow]")
        self.console.print(f"  Retomar Extração Interrompida: [yellow]{'Sim' if config.RESUME_EXTRACTION else 'Não'}[/yellow]")
        self.console.print(f"  Arquivos de Saída:")
        self.console.print(f"    - CSV: [yellow]{config.OUTPUT_FILE}[/yellow]")
        self.console.print(f"    - TXT: [yellow]{config.OUTPUT_TXT}[/yellow]")
        self.console.print(f"    - Mapa do Site: [yellow]{config.SITE_MAP_FILE}[/yellow]\n")