# -*- coding: utf-8 -*-
"""
Coletor e Relator de Estatísticas

Este módulo implementa funcionalidades para coletar estatísticas durante a execução
e gerar relatórios formatados com informações detalhadas sobre o processo.

Uso:
    from utils.stats import StatsReporter, StatsCollector
    
    # Coletar estatísticas
    stats = StatsCollector()
    stats.increment("requests_made")
    
    # Exibir relatório
    reporter = StatsReporter(console)
    reporter.show_summary(stats.get_stats(), pages)
"""

import time
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

try:
    import psutil
except ImportError:
    psutil = None

@dataclass
class StatsCollector:
    """
    Coletor de estatísticas de execução.
    
    Attributes:
        stats: Dicionário com estatísticas
    """
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "layouts_processed": 0,
        "requests_made": 0,
        "request_errors": 0,
        "retries": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "start_time": None,
        "end_time": None
    })
    
    def start_timer(self):
        """Inicia o cronômetro de execução."""
        self.stats["start_time"] = time.time()
    
    def stop_timer(self):
        """Para o cronômetro de execução."""
        self.stats["end_time"] = time.time()
    
    def increment(self, key: str, amount: int = 1):
        """
        Incrementa um contador específico.
        
        Args:
            key: Nome do contador a ser incrementado
            amount: Quantidade a incrementar (padrão = 1)
        """
        if key in self.stats:
            self.stats[key] += amount
    
    def set(self, key: str, value: Any):
        """
        Define um valor específico para uma estatística.
        
        Args:
            key: Nome da estatística
            value: Valor a ser definido
        """
        self.stats[key] = value
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtém todas as estatísticas coletadas.
        
        Returns:
            Dicionário com todas as estatísticas
        """
        return self.stats
    
    def get_execution_time(self) -> float:
        """
        Calcula o tempo de execução.
        
        Returns:
            Tempo de execução em segundos, ou 0 se o timer não foi iniciado/parado
        """
        if self.stats["start_time"] and self.stats["end_time"]:
            return self.stats["end_time"] - self.stats["start_time"]
        return 0.0


class StatsReporter:
    """Gerador de relatórios a partir de estatísticas coletadas."""
    
    def __init__(self, console: Console):
        """
        Inicializa o gerador de relatórios.
        
        Args:
            console: Instância de Rich Console para output
        """
        self.console = console
    
    def _get_memory_usage(self) -> str:
        """
        Obtém o uso de memória atual do processo.
        
        Returns:
            String formatada com o uso de memória em MB, ou "N/A" se não for possível obter
        """
        try:
            if psutil:
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                return f"{memory_mb:.1f} MB"
        except Exception:
            pass
        
        return "N/A"
    
    def show_summary(self, stats: Dict[str, Any], pages: List[Dict[str, Any]]):
        """
        Exibe um resumo detalhado da extração.
        
        Args:
            stats: Dicionário com estatísticas coletadas
            pages: Lista de páginas extraídas
        """
        # Calcular estatísticas
        total_pages = len(pages)
        private_pages = len([p for p in pages if p['private']])
        public_pages = total_pages - private_pages
        
        execution_time = stats.get("end_time", 0) - stats.get("start_time", 0) if stats.get("end_time") else 0
        pages_per_second = total_pages / execution_time if execution_time > 0 else 0
        
        # Calcular eficiência do cache
        cache_hits = stats.get("cache_hits", 0)
        cache_misses = stats.get("cache_misses", 0)
        total_cache = cache_hits + cache_misses
        cache_efficiency = (cache_hits / total_cache) * 100 if total_cache > 0 else 0
        
        # Obter uso de memória
        memory_usage = self._get_memory_usage()
        
        # Criar tabela de estatísticas
        table = Table(title="Resumo da Extração de URLs", box=box.ROUNDED)
        
        # Adicionar colunas
        table.add_column("Estatística", style="cyan")
        table.add_column("Valor", style="green")
        
        # Adicionar linhas com dados
        table.add_row("Total de Páginas", f"{total_pages}")
        table.add_row("Páginas Públicas", f"{public_pages}")
        table.add_row("Páginas Privadas", f"{private_pages}")
        table.add_row("Requisições Realizadas", f"{stats.get('requests_made', 0)}")
        table.add_row("Erros de Requisição", f"{stats.get('request_errors', 0)}")
        table.add_row("Retentativas", f"{stats.get('retries', 0)}")
        table.add_row("Cache Hits", f"{cache_hits}")
        table.add_row("Cache Misses", f"{cache_misses}")
        table.add_row("Eficiência do Cache", f"{cache_efficiency:.1f}%")
        table.add_row("Tempo de Execução", f"{execution_time:.2f} segundos")
        table.add_row("Velocidade", f"{pages_per_second:.2f} páginas/segundo")
        table.add_row("Uso de Memória", memory_usage)
        
        # Exibir a tabela
        self.console.print("\n")
        self.console.print(Panel(table, title="[bold green]Extração Concluída[/]", subtitle="[italic]Liferay URL Extractor[/]"))