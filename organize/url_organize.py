# -*- coding: utf-8 -*-
"""
URL Management Tool - Ferramenta Unificada de Gerenciamento de URLs

Este script unifica diversas funcionalidades para gerenciar URLs de um site Liferay:
1. Reorganização de URLs baseada em hierarquia de planilha Excel
2. Geração de CSV com URLs de destino
3. Verificação de disponibilidade de URLs (404 check) -- esse aqui ta bugado usa o conferir.py
4. Construção de hierarquia de URLs para visualização
5. Correspondência entre URLs de origem e destino

"""

import sys
import os
import re
import csv
import asyncio
import pandas as pd
import aiohttp
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple, Set, Any
import shutil
from pathlib import Path
import time

# Verificar se as bibliotecas necessárias estão instaladas
try:
    import openpyxl
    from dotenv import load_dotenv
except ImportError:
    print("Instalando dependências necessárias...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "python-dotenv", "rich", "aiohttp", "pandas"])
    import openpyxl
    from dotenv import load_dotenv

# Inicialização do console Rich
console = Console()

# Carregar variáveis de ambiente
load_dotenv()

class Logger:
    """Classe para logging com suporte a Rich Console."""
    
    def __init__(self, output_dir: str = None):
        """
        Inicializa o logger.
        
        Args:
            output_dir: Diretório para salvar o log (opcional)
        """
        self.console = Console()
        
        # Configurar arquivo de log
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            self.log_file = os.path.join(output_dir, f"log_{timestamp}.txt")
        else:
            self.log_file = f"log_{timestamp}.txt"
    
    def info(self, message: str):
        """Registra uma mensagem informativa."""
        self.console.print(f"[cyan][INFO][/cyan] {message}")
        self._write_to_file("INFO", message)
    
    def success(self, message: str):
        """Registra uma mensagem de sucesso."""
        self.console.print(f"[green][SUCESSO][/green] {message}")
        self._write_to_file("SUCESSO", message)
    
    def warn(self, message: str):
        """Registra uma mensagem de aviso."""
        self.console.print(f"[yellow][AVISO][/yellow] {message}")
        self._write_to_file("AVISO", message)
    
    def error(self, message: str):
        """Registra uma mensagem de erro."""
        self.console.print(f"[red][ERRO][/red] {message}")
        self._write_to_file("ERRO", message)
    
    def _write_to_file(self, level: str, message: str):
        """Escreve a mensagem no arquivo de log."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{level}] {message}\n")
        except Exception as e:
            self.console.print(f"[red]Erro ao escrever no arquivo de log: {str(e)}[/red]")


class URLProcessor:
    """Classe principal para processar URLs de diferentes maneiras."""
    
    def __init__(self, output_dir: str = None):
        """
        Inicializa o processador de URLs.
        
        Args:
            output_dir: Diretório para salvar os arquivos de saída
        """
        # Configura o diretório de saída
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = f"url_processed_{self.timestamp}"
        
        # Garante que o diretório de saída exista
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Inicializa o logger
        self.logger = Logger(self.output_dir)
        
        # Configurações
        self.max_concurrent_requests = 10
    
    def clean_url(self, url: str) -> str:
        """
        Limpa e normaliza uma URL, removendo protocolo, domínio, etc.
        """
        if not url:
            return ""
        # Convert to string to handle non-string inputs (e.g., numbers)
        url = str(url)
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')
        return path.lower()
        
    def simplify_url(self, url: str) -> str:
        """
        Simplifica uma URL mantendo apenas o domínio e o último segmento do caminho.
        
        Args:
            url: URL a ser simplificada
            
        Returns:
            URL simplificada
        """
        parsed = urlparse(url)
        
        # Obter o caminho da URL e remover barras inicial e final
        path = parsed.path.strip('/')
        
        if not path:
            # Se o caminho está vazio, retornar apenas o domínio
            return f"{parsed.scheme}://{parsed.netloc}"
        
        # Dividir o caminho em segmentos
        segments = path.split('/')
        
        # Verificar se é a página inicial
        if segments[-1] in ['pagina-inicial', 'index', ''] or not segments[-1]:
            return f"{parsed.scheme}://{parsed.netloc}"
        
        # Pegar apenas o último segmento significativo
        last_segment = segments[-1]
        
        # Verificar se o último segmento é apenas um número ou string vazia
        if not last_segment or last_segment.isdigit():
            # Nesse caso, usar o penúltimo segmento, se disponível
            if len(segments) > 1:
                last_segment = segments[-2]
            else:
                # Se não houver segmento significativo, retornar apenas o domínio
                return f"{parsed.scheme}://{parsed.netloc}"
        
        # Reconstruir a URL com apenas o último segmento significativo
        return f"{parsed.scheme}://{parsed.netloc}/{last_segment}"
    
    def _remove_accents(self, text: str) -> str:
        """
        Remove acentos de um texto.
        
        Args:
            text: Texto a ser normalizado
            
        Returns:
            Texto sem acentos
        """
        # Mapeamento simples de caracteres acentuados para não acentuados
        accents = {
            'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
            'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
            'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n'
        }
        
        for accent, no_accent in accents.items():
            text = text.replace(accent, no_accent)
            
        return text
    
    # FUNCIONALIDADE 1: REORGANIZAÇÃO DE HIERARQUIA
    
    async def reorganize_hierarchy(self, 
                                  input_file: str, 
                                  excel_file: str, 
                                  output_file: str = None,
                                  sheet_name: str = None) -> str:
        """
        Reorganiza URLs baseado em hierarquia definida em uma planilha Excel.
        
        Args:
            input_file: Arquivo com as URLs a serem reorganizadas
            excel_file: Arquivo Excel com a hierarquia
            output_file: Arquivo de saída (opcional)
            sheet_name: Nome da planilha no Excel (opcional)
            
        Returns:
            Caminho do arquivo de saída
        """
        self.logger.info(f"Iniciando reorganização de hierarquia...")
        
        # Configura o nome do arquivo de saída
        if not output_file:
            output_file = os.path.join(self.output_dir, "reorganized_urls.txt")
        
        # 1. Carregar URLs do arquivo de entrada
        urls = self._load_urls_from_file(input_file)
        if not urls:
            self.logger.error(f"Não foi possível carregar URLs do arquivo {input_file}")
            return None
        
        # 2. Carregar hierarquia da planilha Excel
        hierarchy_data = self._load_excel_hierarchy(excel_file, sheet_name)
        if not hierarchy_data:
            self.logger.error(f"Não foi possível carregar hierarquia da planilha {excel_file}")
            return None
        
        # 3. Processar dados de hierarquia
        ordered_hierarchies = self._process_hierarchy_data(hierarchy_data)
        
        # 4. Categorizar URLs
        categorized_urls = self._categorize_urls(urls, ordered_hierarchies)
        
        # 5. Salvar URLs reorganizadas
        success = self._save_reorganized_urls(categorized_urls, ordered_hierarchies, output_file)
        
        if success:
            self.logger.success(f"URLs reorganizadas salvas em {output_file}")
            return output_file
        else:
            self.logger.error(f"Falha ao salvar URLs reorganizadas")
            return None
    
    def _load_urls_from_file(self, input_file: str) -> List[str]:
        """
        Carrega URLs de um arquivo de texto.
        
        Args:
            input_file: Caminho do arquivo
            
        Returns:
            Lista de URLs
        """
        self.logger.info(f"Carregando URLs do arquivo {input_file}...")
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            
            self.logger.success(f"Carregadas {len(urls)} URLs do arquivo")
            return urls
        except Exception as e:
            self.logger.error(f"Erro ao carregar URLs: {str(e)}")
            return []
    
    def _load_excel_hierarchy(self, excel_file: str, sheet_name: str = None) -> List[str]:
        """
        Carrega hierarquia de uma planilha Excel (coluna G a partir da linha 3).
        
        Args:
            excel_file: Caminho da planilha Excel
            sheet_name: Nome da planilha (opcional)
            
        Returns:
            Lista de hierarquias
        """
        self.logger.info(f"Carregando hierarquia da planilha {excel_file}...")
        
        try:
            # Ler a planilha Excel - definindo skiprows=2 para começar da linha 3
            if sheet_name:
                self.logger.info(f"Usando planilha: {sheet_name}")
                df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=2)
            else:
                df = pd.read_excel(excel_file, skiprows=2)
            
            # Verificar se a coluna G (Hierarquia) existe
            if 'Hierarquia' in df.columns:
                hierarchy_data = df['Hierarquia'].dropna().tolist()
                self.logger.success(f"Hierarquia carregada com sucesso da coluna 'Hierarquia'. {len(hierarchy_data)} entradas encontradas.")
            elif 'G' in df.columns:  # Tentar pelo índice da coluna
                hierarchy_data = df['G'].dropna().tolist()
                self.logger.success(f"Hierarquia carregada com sucesso da coluna 'G'. {len(hierarchy_data)} entradas encontradas.")
            else:
                # Tentar pelo índice numérico da coluna (G é a 7ª coluna, índice 6)
                if len(df.columns) > 6:
                    hierarchy_data = df.iloc[:, 6].dropna().tolist()
                    self.logger.success(f"Hierarquia carregada com sucesso da 7ª coluna. {len(hierarchy_data)} entradas encontradas.")
                else:
                    self.logger.error(f"Não foi possível encontrar a coluna G na planilha.")
                    return []
            
            return hierarchy_data
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar hierarquia da planilha: {str(e)}")
            return []
    
    def _process_hierarchy_data(self, hierarchy_data: List[str]) -> List[str]:
        """
        Processa dados da hierarquia da planilha.
        
        Args:
            hierarchy_data: Lista de hierarquias da planilha
            
        Returns:
            Lista ordenada de hierarquias únicas
        """
        self.logger.info("Processando dados de hierarquia...")
        
        # Extrair hierarquias únicas e organizá-las
        unique_hierarchies = []
        for hierarchy in hierarchy_data:
            if isinstance(hierarchy, str) and hierarchy.strip():
                # Remover "Raiz >" se presente
                if hierarchy.startswith("Raiz >"):
                    hierarchy = hierarchy[6:].strip()
                
                # Adicionar à lista de hierarquias únicas se ainda não estiver lá
                if hierarchy not in unique_hierarchies:
                    unique_hierarchies.append(hierarchy)
        
        # Extrair categorias principais (primeiro nível sem ">")
        main_categories = set()
        for hierarchy in unique_hierarchies:
            parts = hierarchy.split(">")
            main_category = parts[0].strip()
            if main_category:
                main_categories.add(main_category)
        
        # Converter para lista e ordenar alfabeticamente (ordem inicial)
        main_categories = sorted(list(main_categories))
        
        # Construir a hierarquia completa e ordenada
        ordered_hierarchies = []
        
        # Primeiro, adicionar as categorias principais
        for category in main_categories:
            ordered_hierarchies.append(category)
            
            # Em seguida, adicionar todas as subcategorias dessa categoria principal
            # Ordenadas primeiro pelo número de níveis, depois alfabeticamente
            subcategories = [h for h in unique_hierarchies if h.startswith(category + " >")]
            subcategories.sort(key=lambda h: (h.count(">"), h.lower()))
            
            ordered_hierarchies.extend(subcategories)
        
        # Adicionar qualquer hierarquia que ainda não foi incluída
        for hierarchy in unique_hierarchies:
            if hierarchy not in ordered_hierarchies:
                ordered_hierarchies.append(hierarchy)
        
        self.logger.success(f"Processadas {len(ordered_hierarchies)} hierarquias únicas")
        
        # Exibir as categorias principais encontradas
        self.logger.info("Categorias principais encontradas na planilha:")
        for category in main_categories:
            self.logger.info(f"  - {category}")
            
        return ordered_hierarchies
    
    def _create_url_patterns(self, ordered_hierarchies: List[str]) -> Dict[str, List[str]]:
        """
        Cria um mapeamento de hierarquias para padrões de URL derivados da planilha.
        
        Args:
            ordered_hierarchies: Lista ordenada de hierarquias
            
        Returns:
            Dicionário mapeando hierarquias para listas de padrões
        """
        pattern_map = defaultdict(list)
        
        # Criar padrões a partir dos termos na hierarquia
        for hierarchy in ordered_hierarchies:
            # Extrair partes da hierarquia (ex: "Institucional > Perfil do Secretário" -> ["Institucional", "Perfil do Secretário"])
            parts = [p.strip() for p in hierarchy.split(">")]
            url_patterns = []
            
            # Criar variações de padrões para cada parte da hierarquia
            for part in parts:
                # Versão original (limpa)
                clean_part = part.lower()
                url_patterns.append(clean_part)
                
                # Versão kebab-case (com hífens)
                kebab_case = clean_part.replace(" ", "-")
                if kebab_case != clean_part:
                    url_patterns.append(kebab_case)
                
                # Versão sem espaços
                no_spaces = clean_part.replace(" ", "")
                if no_spaces != clean_part:
                    url_patterns.append(no_spaces)
                
                # Versão com caminho de categoria
                url_patterns.append(f"category/{clean_part.replace(' ', '-')}")
                url_patterns.append(f"category/{clean_part.replace(' ', '')}")
                
                # Versão sem acentos
                normalized = self._remove_accents(clean_part)
                if normalized != clean_part:
                    url_patterns.append(normalized)
                    url_patterns.append(normalized.replace(" ", "-"))
                    url_patterns.append(normalized.replace(" ", ""))
            
            # Adicionar os padrões ao mapeamento para esta hierarquia
            pattern_map[hierarchy].extend(url_patterns)
        
        return pattern_map
    
    def _categorize_urls(self, urls: List[str], ordered_hierarchies: List[str]) -> Dict[str, List[str]]:
        """
        Categoriza URLs de acordo com a hierarquia da planilha.
        
        Args:
            urls: Lista de URLs a categorizar
            ordered_hierarchies: Lista ordenada de hierarquias
            
        Returns:
            Dicionário mapeando categorias para listas de URLs
        """
        self.logger.info("Categorizando URLs de acordo com a hierarquia da planilha...")
        
        # Dicionário para armazenar URLs categorizadas
        categorized_urls = defaultdict(list)
        
        # Criar mapeamento de termos para URLs
        pattern_map = self._create_url_patterns(ordered_hierarchies)
        
        # Para cada URL, encontrar a categoria mais específica
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.logger.console
        ) as progress:
            task = progress.add_task("[cyan]Categorizando URLs...", total=len(urls))
            
            for url in urls:
                progress.update(task, advance=1)
                
                path = urlparse(url).path.lower()
                
                # Encontrar a melhor correspondência na hierarquia
                best_match = "Outros"  # Categoria padrão se não houver correspondência
                best_match_score = 0
                
                for hierarchy, patterns in pattern_map.items():
                    for pattern in patterns:
                        if pattern in path:
                            # Calcular pontuação com base na especificidade do padrão
                            score = len(pattern)
                            if score > best_match_score:
                                best_match = hierarchy
                                best_match_score = score
                
                # Adicionar URL à categoria correspondente
                categorized_urls[best_match].append(url)
        
        # Ordenar URLs dentro de cada categoria
        for category in categorized_urls:
            categorized_urls[category].sort(key=lambda url: (urlparse(url).path.count('/'), urlparse(url).path))
        
        self.logger.success(f"URLs categorizadas em {len(categorized_urls)} seções")
        return categorized_urls
    
    def _save_reorganized_urls(self, 
                              categorized_urls: Dict[str, List[str]], 
                              ordered_hierarchies: List[str], 
                              output_file: str) -> bool:
        """
        Salva as URLs reorganizadas no arquivo de saída.
        
        Args:
            categorized_urls: Dicionário de URLs categorizadas
            ordered_hierarchies: Lista ordenada de hierarquias
            output_file: Caminho do arquivo de saída
            
        Returns:
            True se o salvamento foi bem-sucedido, False caso contrário
        """
        self.logger.info(f"Salvando URLs reorganizadas em {output_file}...")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Escrever as URLs na ordem da hierarquia
                
                # Primeiro, verificar se "Página inicial" ou equivalente existe
                home_categories = ["Página inicial", "Pagina inicial", "Home", "Início", "Inicio"]
                for home_cat in home_categories:
                    if home_cat in categorized_urls:
                        self._write_category(f, home_cat, categorized_urls[home_cat])
                        break
                
                # Depois escrever na ordem da hierarquia definida na planilha
                categories_written = set(home_categories)
                
                for hierarchy in ordered_hierarchies:
                    if hierarchy in categorized_urls and hierarchy not in categories_written:
                        self._write_category(f, hierarchy, categorized_urls[hierarchy])
                        categories_written.add(hierarchy)
                
                # Finalmente, escrever todas as categorias restantes
                for category in sorted(categorized_urls.keys()):
                    if category not in categories_written:
                        self._write_category(f, category, categorized_urls[category])
                        
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar URLs reorganizadas: {str(e)}")
            return False
    
    def _write_category(self, file, category: str, urls: List[str]):
        """
        Escreve uma categoria de URLs no arquivo.
        
        Args:
            file: Arquivo de saída
            category: Nome da categoria
            urls: Lista de URLs nesta categoria
        """
        if not urls:
            return
            
        # Adicionar um separador visual
        file.write(f"\n# {category.upper()}\n")
        
        # Escrever URLs simplificadas
        unique_urls = set()  # Para evitar URLs duplicadas após simplificação
        
        for url in urls:
            simplified_url = self.simplify_url(url)
            
            # Adicionar à lista apenas se ainda não estiver lá
            if simplified_url not in unique_urls:
                file.write(f"{simplified_url}\n")
                unique_urls.add(simplified_url)
    
    # FUNCIONALIDADE 2: GERAÇÃO DE CSV COM URLS DE DESTINO
    
    async def generate_destination_csv(self, 
                                      input_file: str, 
                                      output_file: str = None) -> str:
        """
        Gera um CSV com URLs de destino a partir de um arquivo de URLs reorganizadas.
        
        Args:
            input_file: Arquivo de URLs reorganizadas
            output_file: Arquivo de saída CSV (opcional)
            
        Returns:
            Caminho do arquivo CSV gerado
        """
        self.logger.info(f"Extraindo URLs do arquivo: {input_file}")
        
        # Configurar arquivo de saída
        if not output_file:
            output_file = os.path.join(self.output_dir, "urls_destino.csv")
        
        # Verificar se o arquivo existe
        if not os.path.exists(input_file):
            self.logger.error(f"Erro: Arquivo {input_file} não encontrado!")
            return None
        
        # Ler o conteúdo do arquivo
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.readlines()
        except Exception as e:
            self.logger.error(f"Erro ao ler o arquivo {input_file}: {str(e)}")
            return None
        
        # Extrair URLs e suas categorias
        urls = []
        current_category = None
        
        for line in content:
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith('# '):
                # Nova categoria
                current_category = line[2:].strip()
            elif line.startswith('http'):
                # URL
                urls.append({
                    'url': line,
                    'category': current_category
                })
        
        # Ordenar URLs por categoria
        urls.sort(key=lambda x: (x['category'] or "", x['url']))
        
        # Salvar em CSV
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Para', 'Categoria'])
                
                for item in urls:
                    writer.writerow([item['url'], item['category']])
            
            self.logger.success(f"Arquivo CSV salvo em: {output_file}")
            self.logger.info(f"Total de URLs extraídas: {len(urls)}")
            self.logger.info(f"Total de categorias: {len(set(item['category'] for item in urls if item['category']))}")
            
            return output_file
        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivo CSV: {str(e)}")
            return None
    
    # FUNCIONALIDADE 3: VERIFICAÇÃO DE URLS (404 CHECK)
    
    async def check_urls(self, urls_file: str, output_file: str = None, max_concurrent: int = 10) -> str:
        """
        Verifica se URLs em um arquivo estão acessíveis ou retornam 404.
        
        Args:
            urls_file: Arquivo com as URLs a verificar
            output_file: Arquivo de saída para URLs não encontradas (opcional)
            max_concurrent: Número máximo de requisições concorrentes
            
        Returns:
            Caminho do arquivo de saída com URLs não encontradas
        """
        self.logger.info(f"Iniciando verificação de URLs do arquivo {urls_file}...")
        
        # Configurar arquivo de saída
        if not output_file:
            output_file = os.path.join(self.output_dir, f"urls_nao_encontradas_{self.timestamp}.txt")
        
        # Carregar URLs do arquivo
        urls = self._load_urls_from_file(urls_file)
        if not urls:
            self.logger.error(f"Não foi possível carregar URLs do arquivo {urls_file}")
            return None
        
        # Inicializar gerenciador de sessão
        session_manager = await self._init_session_manager(max_concurrent)
        urls_not_found = []
        
        try:
            # Verificar cada URL
            self.logger.info(f"Verificando {len(urls)} URLs...")
            
            # Processar em lotes para evitar sobrecarga
            batch_size = 50
            total_batches = (len(urls) + batch_size - 1) // batch_size
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.logger.console
            ) as progress:
                task = progress.add_task("[cyan]Verificando URLs...", total=total_batches)
                
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i+batch_size]
                    batch_tasks = [self._check_url(session_manager, url) for url in batch]
                    batch_results = await asyncio.gather(*batch_tasks)
                    
                    # Coletar URLs não encontradas
                    for j, exists in enumerate(batch_results):
                        if not exists:
                            urls_not_found.append(batch[j])
                    
                    progress.update(task, advance=1)
            
            # Salvar URLs não encontradas
            self.logger.info(f"Verificação concluída. {len(urls_not_found)} URLs não foram encontradas.")
            
            await self._save_not_found_urls(urls_not_found, output_file)
            return output_file
            
        finally:
            # Fechar sessão HTTP
            await self._close_session_manager(session_manager)
    
    async def _init_session_manager(self, max_concurrent: int = 10):
        """
        Inicializa o gerenciador de sessão HTTP.
        
        Args:
            max_concurrent: Número máximo de requisições concorrentes
            
        Returns:
            Dicionário com sessão e semáforo
        """
        self.logger.info("Inicializando sessão HTTP...")
        
        # Definir configurações de conexão
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=max_concurrent
        )
        
        # Definir timeout para evitar requisições travadas
        timeout = aiohttp.ClientTimeout(total=30)  # 30 segundos de timeout
        
        # Criar sessão
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        
        # Criar semáforo para limitar requisições concorrentes
        request_semaphore = asyncio.Semaphore(max_concurrent)
        
        return {
            'session': session,
            'semaphore': request_semaphore
        }
    
    async def _close_session_manager(self, session_manager):
        """
        Fecha a sessão HTTP.
        
        Args:
            session_manager: Gerenciador de sessão a ser fechado
        """
        self.logger.info("Fechando sessão HTTP...")
        if 'session' in session_manager and session_manager['session']:
            await session_manager['session'].close()
    
    async def _check_url(self, session_manager, url: str, max_retries: int = 2) -> bool:
        """
        Verifica se uma URL está acessível (não retorna 404).
        
        Args:
            session_manager: Gerenciador de sessão HTTP
            url: URL para verificar
            max_retries: Número máximo de tentativas
            
        Returns:
            True se a página existe, False se retornar 404 ou erro
        """
        # Adicionar esquema HTTP se não estiver presente
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Usar o semáforo para limitar requisições concorrentes
        async with session_manager['semaphore']:
            for attempt in range(max_retries):
                try:
                    # Executar a requisição
                    async with session_manager['session'].get(url, allow_redirects=True) as response:
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
                                # Se for outro código diferente de 200 e 404, consideramos como "não existe"
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
    
    async def _save_not_found_urls(self, urls_not_found: List[str], output_file: str) -> bool:
        """
        Salva as URLs não encontradas no arquivo de saída.
        
        Args:
            urls_not_found: Lista de URLs que retornaram 404
            output_file: Caminho do arquivo de saída
            
        Returns:
            True se o salvamento foi bem-sucedido, False caso contrário
        """
        self.logger.info(f"Salvando URLs não encontradas em {output_file}...")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# URLs não encontradas - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for url in urls_not_found:
                    f.write(f"{url}\n")
            
            self.logger.success(f"URLs não encontradas salvas em {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar URLs não encontradas: {str(e)}")
            return False
    
    # FUNCIONALIDADE 4: CONSTRUÇÃO DE HIERARQUIA DE URLS
    
    async def build_hierarchy(self, 
                             urls_csv: str, 
                             output_file: str = None) -> str:
        """
        Constrói uma visualização hierárquica das URLs a partir do CSV.
        
        Args:
            urls_csv: Arquivo CSV com URLs e categorias
            output_file: Arquivo de saída para a hierarquia (opcional)
            
        Returns:
            Caminho do arquivo de hierarquia gerado
        """
        self.logger.info(f"Construindo hierarquia a partir do arquivo CSV {urls_csv}...")
        
        # Configurar arquivo de saída
        if not output_file:
            output_file = os.path.join(self.output_dir, "hierarquia_urls.txt")
        
        # Verificar se o arquivo existe
        if not os.path.exists(urls_csv):
            self.logger.error(f"Erro: Arquivo CSV {urls_csv} não encontrado!")
            return None
        
        # Ler o arquivo CSV
        try:
            with open(urls_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [(row.get('Para', ''), row.get('Categoria', '')) for row in reader]
        except Exception as e:
            self.logger.error(f"Erro ao ler o arquivo CSV {urls_csv}: {str(e)}")
            return None
        
        # Construir a hierarquia
        hierarchy = self._build_hierarchy_structure(rows)
        
        # Salvar a hierarquia
        success = self._save_hierarchy(hierarchy, output_file)
        
        if success:
            self.logger.success(f"Hierarquia salva em {output_file}")
            return output_file
        else:
            self.logger.error(f"Falha ao salvar hierarquia")
            return None
    
    def _build_hierarchy_structure(self, rows: List[Tuple[str, str]]) -> Dict[tuple, List[str]]:
        """
        Constrói a estrutura de hierarquia a partir das linhas do CSV.
        
        Args:
            rows: Lista de tuplas (url, categoria)
            
        Returns:
            Dicionário mapeando caminhos de categoria para listas de URLs
        """
        self.logger.info("Processando estrutura hierárquica...")
        
        hierarchy = defaultdict(list)
        for url, category in rows:
            if not category:
                # Se não tiver categoria, usar "Sem categoria"
                parts = ["Sem categoria"]
            else:
                # Dividir a categoria em partes
                parts = [part.strip() for part in category.split('>')]
            
            # Adicionar URL ao caminho da categoria
            hierarchy[tuple(parts)].append(url)
        
        self.logger.success(f"Estrutura hierárquica processada com {len(hierarchy)} nós")
        return hierarchy
    
    def _save_hierarchy(self, hierarchy: Dict[tuple, List[str]], output_file: str) -> bool:
        """
        Salva a hierarquia no arquivo de saída.
        
        Args:
            hierarchy: Dicionário de hierarquia
            output_file: Caminho do arquivo de saída
            
        Returns:
            True se o salvamento foi bem-sucedido, False caso contrário
        """
        self.logger.info(f"Salvando hierarquia em {output_file}...")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for category_path in sorted(hierarchy.keys(), key=lambda x: (len(x), x)):
                    # Definir indentação baseada no nível da categoria
                    indent = '  ' * (len(category_path) - 1)
                    
                    # Escrever categoria
                    if len(category_path) == 1:
                        f.write(f"\n{category_path[0]}\n")
                        f.write("-" * len(category_path[0]) + "\n")
                    else:
                        f.write(f"{indent}• {category_path[-1]}\n")
                    
                    # Escrever URLs
                    for url in hierarchy[category_path]:
                        url_indent = '  ' * len(category_path)
                        f.write(f"{url_indent}- {url}\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar hierarquia: {str(e)}")
            return False
        
    async def match_urls(self, 
                        source_xlsx: str, 
                        destination_csv: str, 
                        output_file: str = None,
                        source_column: int = 0,
                        skip_rows: int = 2) -> str:
        """
        Cria uma correspondência entre URLs de origem e destino.
        
        Args:
            source_xlsx: Arquivo Excel com URLs de origem
            destination_csv: Arquivo CSV com URLs de destino
            output_file: Arquivo de saída Excel (opcional)
            source_column: Índice da coluna com URLs de origem (padrão: 0)
            skip_rows: Número de linhas a pular no arquivo de origem (padrão: 2)
            
        Returns:
            Caminho do arquivo de correspondência gerado
        """
        self.logger.info(f"Criando correspondência entre URLs de origem e destino...")
        
        # Configurar arquivo de saída
        if not output_file:
            output_file = os.path.join(self.output_dir, "correspondencia_urls.xlsx")
        
        # Verificar se os arquivos existem
        if not os.path.exists(source_xlsx):
            self.logger.error(f"Erro: Arquivo Excel {source_xlsx} não encontrado!")
            return None
        
        if not os.path.exists(destination_csv):
            self.logger.error(f"Erro: Arquivo CSV {destination_csv} não encontrado!")
            return None
        
        # Carregar URLs de destino do CSV
        try:
            csv_df = pd.read_csv(destination_csv)
            if 'Para' not in csv_df.columns:
                self.logger.error(f"Erro: Coluna 'Para' não encontrada no arquivo CSV")
                return None
                
            # Pegar URLs do CSV e criar dicionário com URLs limpas
            csv_urls = csv_df['Para'].tolist()
            csv_clean = {self.clean_url(url): url for url in csv_urls if url}
            
            self.logger.success(f"Carregadas {len(csv_urls)} URLs de destino")
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar URLs de destino: {str(e)}")
            return None
        
        # Carregar URLs de origem do Excel
        try:
            xlsx_df = pd.read_excel(source_xlsx, header=None, usecols=[source_column], skiprows=skip_rows)
            xlsx_urls = xlsx_df.iloc[:, 0].astype(str).dropna().tolist()
            
            self.logger.success(f"Carregadas {len(xlsx_urls)} URLs de origem")
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar URLs de origem: {str(e)}")
            return None
        
        # Criar correspondências
        self.logger.info("Criando correspondências entre URLs...")
        resultado = []
        
        for orig_url in xlsx_urls:
            clean_orig = self.clean_url(orig_url)
            match_url = csv_clean.get(clean_orig, '')
            resultado.append({'De': orig_url, 'Para': match_url})
        
        # Salvar resultado
        try:
            output_df = pd.DataFrame(resultado)
            output_df.to_excel(output_file, index=False)
            
            self.logger.success(f"Correspondências salvas em {output_file}")
            self.logger.info(f"Total de URLs processadas: {len(resultado)}")
            
            # Estatísticas
            matched = sum(1 for r in resultado if r['Para'])
            self.logger.info(f"URLs com correspondência: {matched} ({matched/len(resultado)*100:.1f}%)")
            self.logger.info(f"URLs sem correspondência: {len(resultado) - matched} ({(len(resultado) - matched)/len(resultado)*100:.1f}%)")
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar correspondências: {str(e)}")
            return None
    
    # FUNCIONALIDADE 5: CORRESPONDÊNCIA ENTRE URLS DE ORIGEM E DESTINO
    
# INTERFACE DE LINHA DE COMANDO (CLI)

async def main():
    """Função principal do script."""
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]Ferramenta Unificada de Gerenciamento de URLs[/bold blue]",
        subtitle="v1.0.0",
        border_style="green"
    ))
    
    # Criar processador de URLs
    processor = URLProcessor()
    
    # Menu de funcionalidades
    while True:
        console.print("\n[bold cyan]Escolha uma funcionalidade:[/bold cyan]")
        console.print("1. Reorganizar URLs por hierarquia da planilha")
        console.print("2. Gerar CSV com URLs de destino")
        console.print("3. Verificar disponibilidade de URLs (404 check)")
        console.print("4. Construir visualização hierárquica de URLs")
        console.print("5. Criar correspondência entre URLs de origem e destino")
        console.print("0. Sair")
        
        choice = Prompt.ask("Opção", choices=["0", "1", "2", "3", "4", "5"], default="0")
        
        if choice == "0":
            console.print("[green]Encerrando programa. Até logo![/green]")
            break
        
        elif choice == "1":
            # Reorganizar URLs por hierarquia
            console.print("\n[bold]REORGANIZAÇÃO DE URLS POR HIERARQUIA[/bold]")
            
            input_file = Prompt.ask("Arquivo de entrada com URLs", default="all_urls.txt")
            excel_file = Prompt.ask("Arquivo Excel com hierarquia", default="hierarchy.xlsx")
            sheet_name = Prompt.ask("Nome da planilha (opcional, deixe em branco para usar a primeira)", default="")
            output_file = Prompt.ask("Arquivo de saída", default="reorganized_urls.txt")
            
            if not sheet_name:
                sheet_name = None
                
            console.print()
            result = await processor.reorganize_hierarchy(input_file, excel_file, output_file, sheet_name)
            
            if result:
                console.print(f"\n[green]✓ URLs reorganizadas salvas em: {result}[/green]")
                
                # Perguntar se deseja gerar CSV com URLs de destino
                if Confirm.ask("Deseja gerar um CSV com as URLs de destino a partir deste arquivo?"):
                    csv_output = await processor.generate_destination_csv(result)
                    if csv_output:
                        console.print(f"[green]✓ CSV com URLs de destino gerado em: {csv_output}[/green]")
            
        elif choice == "2":
            # Gerar CSV com URLs de destino
            console.print("\n[bold]GERAÇÃO DE CSV COM URLS DE DESTINO[/bold]")
            
            input_file = Prompt.ask("Arquivo com URLs reorganizadas", default="reorganized_urls.txt")
            output_file = Prompt.ask("Arquivo CSV de saída", default="urls_destino.csv")
            
            console.print()
            result = await processor.generate_destination_csv(input_file, output_file)
            
            if result:
                console.print(f"\n[green]✓ CSV com URLs de destino gerado em: {result}[/green]")
                
                # Perguntar se deseja construir hierarquia
                if Confirm.ask("Deseja construir uma visualização hierárquica a partir deste CSV?"):
                    hierarchy_output = await processor.build_hierarchy(result)
                    if hierarchy_output:
                        console.print(f"[green]✓ Visualização hierárquica gerada em: {hierarchy_output}[/green]")
            
        elif choice == "3":
            # Verificar URLs (404 check)
            console.print("\n[bold]VERIFICAÇÃO DE DISPONIBILIDADE DE URLS (404 CHECK)[/bold]")
            
            input_file = Prompt.ask("Arquivo com URLs para verificar", default="urls_destino.csv")
            output_file = Prompt.ask("Arquivo de saída para URLs não encontradas", default="urls_nao_encontradas.txt")
            max_concurrent = int(Prompt.ask("Número máximo de requisições concorrentes", default="10"))
            
            console.print()
            result = await processor.check_urls(input_file, output_file, max_concurrent)
            
            if result:
                console.print(f"\n[green]✓ URLs não encontradas salvas em: {result}[/green]")
            
        elif choice == "4":
            # Construir visualização hierárquica
            console.print("\n[bold]CONSTRUÇÃO DE VISUALIZAÇÃO HIERÁRQUICA[/bold]")
            
            input_file = Prompt.ask("Arquivo CSV com URLs e categorias", default="urls_destino.csv")
            output_file = Prompt.ask("Arquivo de saída para a hierarquia", default="hierarquia_urls.txt")
            
            console.print()
            result = await processor.build_hierarchy(input_file, output_file)
            
            if result:
                console.print(f"\n[green]✓ Visualização hierárquica gerada em: {result}[/green]")
            
        elif choice == "5":
            # Criar correspondência entre URLs
            console.print("\n[bold]CORRESPONDÊNCIA ENTRE URLS DE ORIGEM E DESTINO[/bold]")
            
            source_file = Prompt.ask("Arquivo Excel com URLs de origem", default="origem.xlsx")
            dest_file = Prompt.ask("Arquivo CSV com URLs de destino", default="urls_destino.csv")
            output_file = Prompt.ask("Arquivo Excel de saída", default="correspondencia_urls.xlsx")
            source_column = int(Prompt.ask("Índice da coluna com URLs no Excel (0 para primeira coluna)", default="0"))
            skip_rows = int(Prompt.ask("Número de linhas a pular no Excel", default="2"))
            
            console.print()
            result = await processor.match_urls(source_file, dest_file, output_file, source_column, skip_rows)
            
            if result:
                console.print(f"\n[green]✓ Correspondências salvas em: {result}[/green]")
        
        # Aguardar antes de voltar ao menu
        console.print("\n[cyan]Pressione Enter para voltar ao menu principal...[/cyan]")
        input()

if __name__ == "__main__":
    # Executar o loop de eventos assíncrono
    asyncio.run(main())

