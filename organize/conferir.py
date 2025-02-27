# -*- coding: utf-8 -*-
"""
Verificador de Páginas Existentes

Este script verifica se páginas web existem ou retornam erro 404 (não encontrada)
e salva os links das páginas não encontradas em um arquivo de texto.

Uso:
    python verificador_paginas.py
"""

import asyncio
import aiohttp
import pandas as pd
from typing import List
from datetime import datetime

class Logger:
    """Classe simples para logging"""
    
    def __init__(self):
        self.log_file = f"log_verificacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    def info(self, message: str):
        print(f"[INFO] {message}")
        self._write_to_file("INFO", message)
    
    def warn(self, message: str):
        print(f"[AVISO] {message}")
        self._write_to_file("AVISO", message)
    
    def error(self, message: str):
        print(f"[ERRO] {message}")
        self._write_to_file("ERRO", message)
    
    def _write_to_file(self, level: str, message: str):
        with open(self.log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] [{level}] {message}\n")


class SessionManager:
    """Gerenciador de sessão HTTP para verificação de páginas."""
    
    def __init__(self, logger: Logger, max_concurrent: int = 10):
        """
        Inicializa o gerenciador de sessão.
        
        Args:
            logger: Logger para registrar operações
            max_concurrent: Número máximo de requisições concorrentes
        """
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
        timeout = aiohttp.ClientTimeout(total=30)  # 30 segundos de timeout
        
        # Criar sessão
        self.session = aiohttp.ClientSession(
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
    
    async def verificar_url(self, url: str, max_retries: int = 2) -> bool:
        """
        Verifica se uma URL está acessível (não retorna 404).
        
        Args:
            url: URL para a requisição
            max_retries: Número máximo de tentativas
            
        Returns:
            True se a página existe, False se retornar 404
        """
        if self.session is None:
            raise RuntimeError("Sessão HTTP não inicializada")
        
        # Adicionar esquema HTTP se não estiver presente
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Usar o semáforo para limitar requisições concorrentes
        async with self.request_semaphore:
            for attempt in range(max_retries):
                try:
                    # Executar a requisição
                    async with self.session.get(url, allow_redirects=True) as response:
                        # Verificar o status da resposta
                        if response.status == 404:
                            # Página não encontrada (404)
                            self.logger.warn(f"Página não encontrada (404): {url}")
                            return False
                        elif response.status == 200:
                            # Página existe
                            return True
                        else:
                            # Outro status
                            self.logger.warn(f"Status inesperado para {url}: {response.status}")
                            if attempt == max_retries - 1:
                                # Se for outro código diferente de 200 e 404, consideramos como "não existe" para ser seguro
                                self.logger.error(f"URL inacessível após {max_retries} tentativas: {url} (Status: {response.status})")
                                return False
                
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    # Erro de conexão ou timeout
                    if attempt == max_retries - 1:
                        self.logger.error(f"Erro ao acessar {url}: {str(e)}")
                        return False
                    
                    # Espera simples entre tentativas
                    await asyncio.sleep(1)
                
                except Exception as e:
                    # Outros erros inesperados
                    self.logger.error(f"Erro inesperado ao acessar {url}: {str(e)}")
                    return False
            
            # Se chegou até aqui, a página não está acessível
            return False


class VerificadorPaginas:
    """Classe para verificar a existência de páginas."""
    
    def __init__(self, arquivo_xlsx: str, logger: Logger):
        """
        Inicializa o verificador de páginas.
        
        Args:
            arquivo_xlsx: Caminho para o arquivo XLSX com os links
            logger: Logger para registrar operações
        """
        self.arquivo_xlsx = arquivo_xlsx
        self.logger = logger
        self.session_manager = SessionManager(logger)
        self.arquivo_resultado = f"paginas_nao_encontradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    async def carregar_links(self) -> List[str]:
        """
        Carrega os links da coluna B do arquivo XLSX.
        
        Returns:
            Lista de links da coluna B
        """
        try:
            self.logger.info(f"Carregando links do arquivo: {self.arquivo_xlsx}")
            df = pd.read_excel(self.arquivo_xlsx)
            
            # Verificar se existe uma coluna B
            if len(df.columns) < 2:
                self.logger.error("O arquivo XLSX não possui uma coluna B")
                return []
            
            # Obter a segunda coluna (coluna B)
            links = df.iloc[:, 1].dropna().tolist()
            
            self.logger.info(f"Carregados {len(links)} links para verificação")
            return links
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar o arquivo XLSX: {str(e)}")
            return []
    
    async def salvar_resultado(self, urls_nao_encontradas: List[str]):
        """
        Salva as URLs não encontradas no arquivo de resultado.
        
        Args:
            urls_nao_encontradas: Lista de URLs que retornaram 404
        """
        try:
            with open(self.arquivo_resultado, 'w', encoding='utf-8') as f:
                f.write(f"# Páginas não encontradas - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for url in urls_nao_encontradas:
                    f.write(f"{url}\n")
            
            self.logger.info(f"Resultado salvo em {self.arquivo_resultado}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar o arquivo de resultado: {str(e)}")
    
    async def executar(self):
        """
        Executa o processo de verificação de todas as páginas.
        """
        await self.session_manager.initialize()
        
        try:
            # Carregar links da planilha
            links = await self.carregar_links()
            if not links:
                self.logger.error("Nenhum link carregado para verificação")
                return
            
            # Verificar cada link
            self.logger.info(f"Iniciando verificação de {len(links)} páginas")
            urls_nao_encontradas = []
            
            # Criar uma lista de tarefas para verificar todas as páginas concorrentemente
            tarefas = []
            resultados = []
            
            # Processar em lotes para não sobrecarregar
            tamanho_lote = 50
            for i in range(0, len(links), tamanho_lote):
                lote = links[i:i+tamanho_lote]
                tarefas_lote = [self.session_manager.verificar_url(url) for url in lote]
                resultados_lote = await asyncio.gather(*tarefas_lote)
                
                # Processar resultados do lote
                for j, existe in enumerate(resultados_lote):
                    if not existe:
                        urls_nao_encontradas.append(lote[j])
                
                self.logger.info(f"Processado lote {i//tamanho_lote + 1}/{(len(links) + tamanho_lote - 1)//tamanho_lote}")
            
            # Salvar resultado
            self.logger.info(f"Verificação concluída. {len(urls_nao_encontradas)} páginas não foram encontradas")
            await self.salvar_resultado(urls_nao_encontradas)
            
        finally:
            # Fechar sessão HTTP
            await self.session_manager.close()


async def main():
    # Configuração do logger
    logger = Logger()
    logger.info("Iniciando verificação de páginas")
    
    # Nome do arquivo XLSX
    arquivo_xlsx = input("Digite o caminho do arquivo XLSX (ou pressione Enter para usar 'correspondencia_urls.xlsx'): ").strip()
    if not arquivo_xlsx:
        arquivo_xlsx = "correspondencia_urls.xlsx"
    
    # Iniciar verificador
    verificador = VerificadorPaginas(arquivo_xlsx, logger)
    await verificador.executar()
    
    logger.info("Processo finalizado")


if __name__ == "__main__":
    # Executar o loop de eventos assíncrono
    asyncio.run(main())