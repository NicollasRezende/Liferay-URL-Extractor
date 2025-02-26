# -*- coding: utf-8 -*-
"""
Gerenciador de Cache

Este módulo implementa funcionalidades de cache para reduzir o número
de requisições ao servidor Liferay, melhorando o desempenho da aplicação.

Uso:
    from core.cache import CacheManager
    cache = CacheManager(cache_dir=".cache", ttl=24, key_prefix="my_cache")
    
    # Verificar e obter do cache
    data = await cache.get_or_fetch("my_key", fetch_func)
"""

import time
import hashlib
import shelve
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from utils.logger import Logger

class CacheManager:
    """Gerenciador de cache para armazenar resultados de requisições."""
    
    def __init__(self, cache_dir: str, ttl: int, logger: Logger, key_prefix: str = "cache"):
        """
        Inicializa o gerenciador de cache.
        
        Args:
            cache_dir: Diretório para armazenar arquivos de cache
            ttl: Tempo de vida em horas (0 = desativado)
            logger: Logger para registrar operações
            key_prefix: Prefixo para chaves de cache (para evitar colisões)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = ttl * 3600  # Converter horas para segundos
        self.logger = logger
        self.key_prefix = key_prefix
        
        # Abrir o banco de dados de cache
        self.cache_db_path = str(self.cache_dir / f"{key_prefix}_db")
        self.cache_db = None
    
    def open(self):
        """Abre a conexão com o banco de dados de cache."""
        if self.cache_db is None:
            self.cache_db = shelve.open(self.cache_db_path)
        return self.cache_db
    
    def close(self):
        """Fecha a conexão com o banco de dados de cache."""
        if self.cache_db is not None:
            self.cache_db.close()
            self.cache_db = None
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Gera uma chave de cache baseada nos argumentos.
        
        Args:
            args: Argumentos posicionais
            kwargs: Argumentos nomeados
            
        Returns:
            String com a chave de cache (hash MD5)
        """
        # Combinar argumentos em uma única string
        key_data = json.dumps([args, kwargs], sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def is_valid(self, cache_time: float) -> bool:
        """
        Verifica se um item em cache ainda é válido.
        
        Args:
            cache_time: Timestamp de quando o item foi armazenado
            
        Returns:
            Boolean indicando se o cache ainda é válido
        """
        # Se TTL = 0, cache está desativado
        if self.ttl <= 0:
            return False
        
        # Verificar se o tempo atual - tempo do cache é menor que TTL
        return (time.time() - cache_time) < self.ttl
    
    async def get_or_fetch(self, key: str, fetch_func: Callable, *args, **kwargs) -> Tuple[Any, bool]:
        """
        Tenta obter dados do cache, ou executa a função para buscá-los.
        
        Args:
            key: Chave de cache
            fetch_func: Função assíncrona para buscar dados se não estiverem em cache
            args: Argumentos posicionais para a função fetch
            kwargs: Argumentos nomeados para a função fetch
            
        Returns:
            Tupla (dados, usou_cache) onde dados são os dados obtidos e usou_cache
            é um booleano indicando se os dados vieram do cache
        """
        full_key = f"{self.key_prefix}_{key}"
        cache_hit = False
        db = self.open()
        
        # Verificar cache
        if self.ttl > 0 and full_key in db:
            cache_data = db[full_key]
            cache_time = cache_data.get('time', 0)
            
            # Verificar se o cache ainda é válido
            if self.is_valid(cache_time):
                self.logger.cache(f"Cache hit para chave: {key}")
                return cache_data.get('content'), True
            else:
                self.logger.cache(f"Cache expirado para chave: {key}")
        
        # Se chegamos aqui, precisamos buscar os dados
        data = await fetch_func(*args, **kwargs)
        
        # Armazenar em cache se TTL > 0
        if self.ttl > 0:
            db[full_key] = {
                'time': time.time(),
                'content': data
            }
            self.logger.cache(f"Atualizado cache para chave: {key}")
        
        return data, False