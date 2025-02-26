# -*- coding: utf-8 -*-
"""
Módulo de configurações do Liferay URL Extractor

Este módulo gerencia todas as configurações da aplicação, carregando-as
de variáveis de ambiente através do arquivo .env ou diretamente do ambiente.
Utiliza a estrutura dataclass para facilitar a organização das configurações.

Uso:
    from config.settings import load_config
    config = load_config()
    print(config.LIFERAY_URL)
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

@dataclass
class AppConfig:
    """Classe de configuração da aplicação."""
    LIFERAY_URL: str
    EMAIL: str
    PASSWORD: str
    GROUP_ID: str
    OUTPUT_FILE: str
    OUTPUT_TXT: str
    SITE_MAP_FILE: str
    MAX_CONCURRENT_REQUESTS: int
    CACHE_DIR: str
    CACHE_TTL: int
    RESUME_EXTRACTION: bool

def load_config() -> AppConfig:
    """
    Carrega as configurações a partir de variáveis de ambiente.
    
    Returns:
        AppConfig: Objeto contendo todas as configurações da aplicação.
    """
    # Carregar variáveis de ambiente do arquivo .env
    load_dotenv()
    
    # Definir configurações com valores padrão
    return AppConfig(
        LIFERAY_URL=os.getenv("LIFERAY_URL", ""),
        EMAIL=os.getenv("EMAIL", ""),
        PASSWORD=os.getenv("PASSWORD", ""),
        GROUP_ID=os.getenv("GROUP_ID", ""),
        OUTPUT_FILE=os.getenv("OUTPUT_FILE", "all_liferay_urls.csv"),
        OUTPUT_TXT=os.getenv("OUTPUT_TXT", "all_urls.txt"),
        SITE_MAP_FILE=os.getenv("SITE_MAP_FILE", "site_structure.html"),
        MAX_CONCURRENT_REQUESTS=int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
        CACHE_DIR=os.getenv("CACHE_DIR", ".cache"),
        CACHE_TTL=int(os.getenv("CACHE_TTL", "24")),
        RESUME_EXTRACTION=os.getenv("RESUME_EXTRACTION", "True").lower() == "true"
    )