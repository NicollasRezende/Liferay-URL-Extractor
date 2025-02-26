# -*- coding: utf-8 -*-
"""
Gerenciador de Sessão HTTP

Este módulo implementa um gerenciador de sessão HTTP para comunicação com a API do Liferay,
adicionando recursos como autenticação, retry, e configurações de timeout.

Uso:
    from core.session import SessionManager
    session_manager = SessionManager(email="user@example.com", password="password", max_concurrent=10)
    await session_manager.initialize()
    
    # Fazer requisição com retry automático
    result = await session_manager.request_with_retry("POST", url, params={...})
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from utils.logger import Logger

class SessionManager:
    """Gerenciador de sessão HTTP para comunicação com o Liferay."""
    
    def __init__(self, email: str, password: str, logger: Logger, max_concurrent: int = 10):
        """
        Inicializa o gerenciador de sessão.
        
        Args:
            email: Email para autenticação na API do Liferay
            password: Senha para autenticação na API do Liferay
            logger: Logger para registrar operações
            max_concurrent: Número máximo de requisições concorrentes
        """
        self.email = email
        self.password = password
        self.logger = logger
        self.max_concurrent = max_concurrent
        self.session = None
        self.request_semaphore = None
    
    async def initialize(self):
        """
        Inicializa a sessão HTTP e o semáforo para controle de concorrência.
        """
        self.logger.info("Inicializando sessão HTTP")
        
        # Definir configurações de conexão
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=self.max_concurrent
        )
        
        # Definir timeout para evitar requisições travadas
        timeout = aiohttp.ClientTimeout(total=60)  # 60 segundos de timeout
        
        # Criar sessão com autenticação básica
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.email, self.password),
            connector=connector,
            timeout=timeout
        )
        
        # Criar semáforo para limitar requisições concorrentes
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def close(self):
        """
        Fecha a sessão HTTP.
        """
        self.logger.info("Fechando sessão HTTP")
        if self.session:
            await self.session.close()
            self.session = None
    
    async def request_with_retry(self, method: str, url: str, params: Optional[Dict[str, Any]] = None,
                                 max_retries: int = 3) -> Any:
        """
        Executa uma requisição HTTP com retry automático em caso de falhas.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL para a requisição
            params: Parâmetros para a requisição
            max_retries: Número máximo de tentativas
            
        Returns:
            Dados JSON da resposta, ou lista vazia em caso de erro
        """
        if self.session is None:
            raise RuntimeError("Sessão HTTP não inicializada")
        
        # Usar o semáforo para limitar requisições concorrentes
        async with self.request_semaphore:
            for attempt in range(max_retries):
                try:
                    # Escolher o método HTTP adequado
                    if method.upper() == "GET":
                        request_method = self.session.get
                    else:
                        request_method = self.session.post
                    
                    # Executar a requisição
                    async with request_method(url, params=params) as response:
                        if response.status in (200, 201):
                            # Requisição bem-sucedida
                            return await response.json()
                        else:
                            # Erro na resposta
                            error_text = await response.text()
                            self.logger.warn(f"Erro na resposta (tentativa {attempt+1}/{max_retries}): Status {response.status}")
                            
                            # Se for a última tentativa, registrar detalhes do erro
                            if attempt == max_retries - 1:
                                self.logger.error(f"Detalhes do erro: {error_text[:200]}...")
                                return []
                
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    # Erro de conexão ou timeout
                    if attempt == max_retries - 1:
                        self.logger.error(f"Falha na requisição após {max_retries} tentativas: {str(e)}")
                        return []
                    
                    # Exponential backoff - espera crescente entre tentativas
                    wait_time = 2 ** attempt  # 1s, 2s, 4s, ...
                    self.logger.warn(f"Tentativa {attempt+1} falhou. Aguardando {wait_time}s antes de tentar novamente...")
                    await asyncio.sleep(wait_time)
                
                except Exception as e:
                    # Outros erros inesperados
                    self.logger.error(f"Erro inesperado: {str(e)}")
                    return []