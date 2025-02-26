#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liferay URL Extractor - Script principal

Este script é o ponto de entrada do aplicativo. Ele inicializa o extrator,
executa o processo de extração e salva os resultados nos formatos desejados.

Uso:
    python main.py

Autor: Seu Nome
Data: Data de Criação/Atualização
"""

import asyncio
import time
import datetime
from rich.console import Console
from rich.panel import Panel

# Importar diretamente dos módulos específicos em vez de usar os __init__.py
from config.settings import load_config
from core.extractor import LiferayUrlExtractor
from utils.logger import Logger
from utils.stats import StatsReporter

# Inicialização do console Rich
console = Console()

async def main():
    """Função principal do aplicativo."""
    # Carregar configurações
    config = load_config()
    
    # Inicializar logger
    logger = Logger(console)
    
    # Exibir banner de início
    console.print(Panel.fit(
        "[bold blue]Liferay URL Extractor[/bold blue] - [italic]Extração completa de URLs[/italic]", 
        subtitle=f"Versão 3.0 - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        border_style="green"
    ))
    
    # Exibir configurações carregadas
    logger.display_config(config)
    
    # Marcar tempo de início
    start_time = time.time()
    
    # Inicializar o extrator
    extractor = LiferayUrlExtractor(
        liferay_url=config.LIFERAY_URL,
        email=config.EMAIL,
        password=config.PASSWORD,
        group_id=config.GROUP_ID,
        logger=logger,
        max_concurrent_requests=config.MAX_CONCURRENT_REQUESTS,
        cache_dir=config.CACHE_DIR,
        cache_ttl=config.CACHE_TTL,
        resume_extraction=config.RESUME_EXTRACTION
    )
    
    # Inicializar sessão HTTP
    await extractor.initialize_session()
    
    try:
        # Buscar todas as páginas
        await extractor.fetch_all_layouts()
        
        # Salvar resultados
        await extractor.save_results(
            csv_file=config.OUTPUT_FILE,
            txt_file=config.OUTPUT_TXT,
            sitemap_file=config.SITE_MAP_FILE
        )
        
        # Mostrar relatório de estatísticas
        stats_reporter = StatsReporter(console)
        stats_reporter.show_summary(extractor.stats, extractor.all_pages)
        
    finally:
        # Garantir que a sessão seja fechada
        await extractor.close_session()
    
    # Calcular e exibir tempo total de execução
    execution_time = time.time() - start_time
    console.print(f"\n[bold green]Processo concluído com sucesso em {execution_time:.2f} segundos![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())