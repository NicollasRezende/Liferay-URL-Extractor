# -*- coding: utf-8 -*-
"""
Extrator de URLs do Liferay

Este é o componente principal que coordena a extração de URLs do Liferay,
gerenciando o fluxo de trabalho e utilizando outros componentes para tarefas especializadas.

Uso:
    from core.extractor import LiferayUrlExtractor
    
    extractor = LiferayUrlExtractor(...)
    await extractor.initialize_session()
    await extractor.fetch_all_layouts()
    await extractor.save_results(...)
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from urllib.parse import urljoin

from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, SpinnerColumn

# Importar diretamente dos módulos específicos em vez de usar os pacotes
from core.session import SessionManager
from core.cache import CacheManager
from utils.logger import Logger
from utils.helpers import save_state, load_state, generate_cache_key, convert_processed_layouts
from models.page import Page

# Importações diretas dos exportadores
from exporters.csv_exporter import CSVExporter 
from exporters.txt_exporter import TXTExporter
from exporters.sitemap_exporter import SitemapExporter

class LiferayUrlExtractor:
    """Extrator principal de URLs do Liferay."""
    
    def __init__(self, liferay_url: str, email: str, password: str, group_id: str,
                 logger: Logger, max_concurrent_requests: int = 10, cache_dir: str = ".cache",
                 cache_ttl: int = 24, resume_extraction: bool = True):
        """
        Inicializa o extrator de URLs do Liferay.
        
        Args:
            liferay_url: URL base do Liferay
            email: Email para autenticação
            password: Senha para autenticação
            group_id: ID do grupo/site no Liferay
            logger: Logger para registrar operações
            max_concurrent_requests: Número máximo de requisições concorrentes
            cache_dir: Diretório para armazenar cache
            cache_ttl: Tempo de vida do cache em horas (0 = desabilitado)
            resume_extraction: Flag para continuar extração interrompida
        """
        self.liferay_url = liferay_url
        self.email = email
        self.password = password
        self.group_id = group_id
        self.logger = logger
        self.max_concurrent_requests = max_concurrent_requests
        
        # Estruturas de dados e contadores
        self.all_pages = []
        self.processed_layouts = set()  # Para evitar processamento duplicado
        self.site_structure = {"public": {}, "private": {}}
        
        # Configuração de cache e estado
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_ttl = cache_ttl
        self.resume_extraction = resume_extraction
        
        # Gerar chave única de cache para este site
        self.cache_key = generate_cache_key(liferay_url, group_id)
        
        # Arquivo de estado para retomar execução
        self.state_file = self.cache_dir / f"state_{self.cache_key}.json"
        
        # Inicializar componentes
        self.session_manager = SessionManager(email, password, logger, max_concurrent_requests)
        self.cache_manager = CacheManager(cache_dir, cache_ttl, logger, self.cache_key)
        
        # Estatísticas
        self.stats = {
            "layouts_processed": 0,
            "requests_made": 0,
            "request_errors": 0,
            "retries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "start_time": None,
            "end_time": None
        }
        
    async def initialize_session(self):
        """
        Inicializa a sessão HTTP e carrega o estado anterior se disponível.
        """
        # Inicializar sessão HTTP
        await self.session_manager.initialize()
        
        # Abrir o cache
        self.cache_manager.open()
        
        # Tentar carregar estado anterior se solicitado
        if self.resume_extraction and self.state_file.exists():
            self.logger.info(f"Tentando recuperar estado anterior de {self.state_file}")
            
            try:
                # Carregar estado do arquivo
                state = load_state(self.state_file)
                
                if state:
                    # Restaurar dados do estado anterior
                    self.all_pages = state.get('all_pages', [])
                    self.processed_layouts = convert_processed_layouts(state.get('processed_layouts', []))
                    self.stats = state.get('stats', self.stats)
                    self.site_structure = state.get('site_structure', {})
                    
                    # Atualizar estatísticas
                    self.logger.success(f"Estado recuperado com sucesso: {len(self.all_pages)} páginas já extraídas")
                    self.logger.info(f"Continuando extração de onde parou...")
            except Exception as e:
                self.logger.error(f"Erro ao carregar estado: {str(e)}")
                self.all_pages = []
                self.processed_layouts = set()
                self.site_structure = {"public": {}, "private": {}}
    
    async def close_session(self):
        """
        Fecha a sessão HTTP e o cache.
        """
        self.logger.info("Fechando sessão HTTP e salvando cache")
        
        # Fechar sessão HTTP
        await self.session_manager.close()
        
        # Fechar cache
        self.cache_manager.close()
    
    def save_current_state(self):
        """
        Salva o estado atual para possibilitar retomada futura.
        """
        try:
            # Usar a função auxiliar para salvar o estado
            if save_state(self.state_file, self.all_pages, self.processed_layouts, 
                          self.stats, self.site_structure):
                self.logger.info(f"Estado atual salvo em {self.state_file}")
            else:
                self.logger.warn(f"Não foi possível salvar o estado atual")
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado: {str(e)}")
    
    async def get_layouts(self, parent_layout_id: int = 0, is_private: bool = False) -> List[Dict[str, Any]]:
        """
        Obtém layouts do Liferay para um determinado parent_layout_id.
        
        Args:
            parent_layout_id: ID do layout pai
            is_private: Flag indicando se são páginas privadas
            
        Returns:
            Lista de layouts (páginas) obtidas da API do Liferay
        """
        # Chave única para este layout
        layout_key = f"{parent_layout_id}-{is_private}"
        
        # Se já processamos este layout, retorna vazio
        if layout_key in self.processed_layouts:
            return []
            
        # Marca como processado
        self.processed_layouts.add(layout_key)
        
        # Chave de cache para esta requisição
        cache_key = f"layout_{self.group_id}_{parent_layout_id}_{is_private}"
        
        # Definir função de busca para o cache
        async def fetch_layouts():
            self.stats["requests_made"] += 1
            url = f"{self.liferay_url}/api/jsonws/layout/get-layouts"
            
            params = {
                'groupId': self.group_id,
                'privateLayout': str(is_private).lower(),
                'parentLayoutId': parent_layout_id
            }
            
            # Executar requisição com retry automático
            result = await self.session_manager.request_with_retry("POST", url, params)
            return result
        
        # Tentar obter do cache ou fazer requisição
        layouts, from_cache = await self.cache_manager.get_or_fetch(cache_key, fetch_layouts)
        
        # Atualizar estatísticas de cache
        if from_cache:
            self.stats["cache_hits"] += 1
        else:
            self.stats["cache_misses"] += 1
        
        return layouts
    
    async def fetch_all_layouts(self):
        """
        Busca todas as páginas públicas e privadas recursivamente.
        """
        # Iniciar cronômetro
        self.stats["start_time"] = time.time()
        
        # Iniciar com progresso visual
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.fields[info]}"),
            console=self.logger.console
        ) as progress:
            task = progress.add_task("[cyan]Extraindo páginas...", total=None, info="Iniciando...")
            
            # Configurar tarefa de salvamento periódico de estado
            update_state_task = asyncio.create_task(self._periodic_state_save(30))
            
            try:
                # Primeiro, obtém as páginas de nível superior (públicas e privadas)
                tasks = [
                    self.get_layouts(0, False),  # Páginas públicas
                    self.get_layouts(0, True)    # Páginas privadas
                ]
                
                top_level_results = await asyncio.gather(*tasks)
                top_level_public = top_level_results[0]
                top_level_private = top_level_results[1]
                
                # Atualizar progresso
                progress.update(task, info=f"Processando {len(top_level_public) + len(top_level_private)} páginas de nível superior")
                
                # Lista para armazenar todas as tarefas de busca de subpáginas
                child_tasks = []
                
                # Processar páginas públicas de nível superior
                for layout in top_level_public:
                    self._process_layout(layout, "", False)
                    layout_id = layout.get('layoutId', 0)
                    friendly_url = layout.get('friendlyURL', '').lstrip('/')
                    
                    # Inicializar estrutura para esta página
                    self.site_structure['public'][friendly_url] = {
                        'id': layout_id,
                        'title': layout.get('name', ''),
                        'children': {}
                    }
                    
                    child_tasks.append(self._fetch_child_layouts(
                        layout_id, 
                        friendly_url, 
                        False, 
                        self.site_structure['public'][friendly_url]['children']
                    ))
                
                # Processar páginas privadas de nível superior
                for layout in top_level_private:
                    self._process_layout(layout, "", True)
                    layout_id = layout.get('layoutId', 0)
                    friendly_url = layout.get('friendlyURL', '').lstrip('/')
                    
                    # Inicializar estrutura para esta página
                    self.site_structure['private'][friendly_url] = {
                        'id': layout_id,
                        'title': layout.get('name', ''),
                        'children': {}
                    }
                    
                    child_tasks.append(self._fetch_child_layouts(
                        layout_id, 
                        friendly_url, 
                        True, 
                        self.site_structure['private'][friendly_url]['children']
                    ))
                
                # Executar todas as tarefas em paralelo com atualização de progresso
                if child_tasks:
                    # Atualizar a barra de progresso para mostrar o total de tarefas
                    progress.update(task, total=len(child_tasks), completed=0)
                    
                    # Executar tarefas com callback para atualizar o progresso
                    completed = 0
                    for child_task in asyncio.as_completed(child_tasks):
                        await child_task
                        completed += 1
                        progress.update(task, completed=completed, 
                                       info=f"Páginas: {self.stats['layouts_processed']} | Cache: ✓{self.stats['cache_hits']} ✗{self.stats['cache_misses']}")
            
            finally:
                # Cancelar tarefa de salvamento periódico
                update_state_task.cancel()
                try:
                    await update_state_task
                except asyncio.CancelledError:
                    pass
        
        # Salvar o estado final
        self.save_current_state()
        
        # Registrar tempo de finalização
        self.stats["end_time"] = time.time()
        execution_time = self.stats["end_time"] - self.stats["start_time"]
        self.logger.success(f"Extração concluída em {execution_time:.2f} segundos")
    
    async def _periodic_state_save(self, interval: int):
        """
        Salva o estado atual periodicamente para possibilitar recuperação.
        
        Args:
            interval: Intervalo em segundos entre salvamentos
        """
        try:
            while True:
                await asyncio.sleep(interval)
                self.save_current_state()
                self.logger.debug(f"Estado salvo automaticamente ({self.stats['layouts_processed']} páginas processadas)")
        except asyncio.CancelledError:
            # Tarefa cancelada normalmente, não é erro
            pass
    
    def _process_layout(self, layout: Dict[str, Any], parent_url: str, is_private: bool):
        """
        Processa um layout individual e o adiciona à lista de páginas.
        
        Args:
            layout: Dados do layout obtido da API
            parent_url: URL da página pai
            is_private: Flag indicando se é uma página privada
        """
        # Criar objeto de página a partir do layout
        page = Page.from_json(layout, parent_url, is_private, self.liferay_url)
        
        # Adicionar à lista de todas as páginas
        self.all_pages.append(page.to_dict())
        
        # Incrementar contador
        self.stats["layouts_processed"] += 1
    
    async def _fetch_child_layouts(self, parent_layout_id: int, parent_url: str, 
                                  is_private: bool, structure_ref: Dict[str, Any]):
        """
        Busca recursivamente as subpáginas de um layout específico.
        
        Args:
            parent_layout_id: ID do layout pai
            parent_url: URL da página pai
            is_private: Flag indicando se são páginas privadas
            structure_ref: Referência para a estrutura do site onde adicionar as subpáginas
        """
        # Obter subpáginas deste layout
        child_layouts = await self.get_layouts(parent_layout_id, is_private)
        
        # Se não há subpáginas, retorna
        if not child_layouts:
            return
        
        # Tarefas para buscar subpáginas adicionais
        tasks = []
        
        # Processar cada subpágina
        for layout in child_layouts:
            self._process_layout(layout, parent_url, is_private)
            layout_id = layout.get('layoutId', 0)
            friendly_url = layout.get('friendlyURL', '').lstrip('/')
            
            # Construir novo caminho
            new_path = f"{parent_url}/{friendly_url}" if parent_url else friendly_url
            
            # Adicionar à estrutura do site
            structure_key = friendly_url
            structure_ref[structure_key] = {
                'id': layout_id,
                'title': layout.get('name', ''),
                'children': {}
            }
            
            # Buscar recursivamente as subpáginas desta página
            tasks.append(self._fetch_child_layouts(
                layout_id, 
                new_path, 
                is_private, 
                structure_ref[structure_key]['children']
            ))
        
        # Executa tarefas para níveis mais profundos em paralelo
        if tasks:
            await asyncio.gather(*tasks)
    
    async def save_results(self, csv_file: str, txt_file: str, sitemap_file: str):
        """
        Salva os resultados da extração em diferentes formatos.
        
        Args:
            csv_file: Caminho para o arquivo CSV
            txt_file: Caminho para o arquivo TXT
            sitemap_file: Caminho para o arquivo HTML do mapa do site
        """
        # Criar exportadores
        csv_exporter = CSVExporter(self.logger)
        txt_exporter = TXTExporter(self.logger)
        sitemap_exporter = SitemapExporter(self.logger, self.liferay_url)
        
        # Executar exportações em paralelo
        await asyncio.gather(
            csv_exporter.export(self.all_pages, csv_file),
            txt_exporter.export(self.all_pages, txt_file),
            sitemap_exporter.export(self.site_structure, sitemap_file)
        )