# -*- coding: utf-8 -*-
"""
Exportador CSV

Este módulo implementa a funcionalidade de exportação de dados para arquivos CSV.

Uso:
    from exporters.csv_exporter import CSVExporter
    
    exporter = CSVExporter(logger)
    await exporter.export(pages, output_file)
"""

import csv
from typing import List, Dict, Any
from utils.logger import Logger

class CSVExporter:
    """Exportador de dados para arquivos CSV."""
    
    def __init__(self, logger: Logger):
        """
        Inicializa o exportador CSV.
        
        Args:
            logger: Logger para registrar operações
        """
        self.logger = logger
    
    async def export(self, pages: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Exporta uma lista de páginas para um arquivo CSV.
        
        Args:
            pages: Lista de páginas para exportar
            output_file: Caminho do arquivo CSV de saída
            
        Returns:
            Boolean indicando sucesso ou falha
        """
        self.logger.info(f"Salvando {len(pages)} URLs em CSV: {output_file}")
        
        try:
            # Ordenar páginas para melhor visualização (por tipo e caminho)
            sorted_pages = sorted(pages, key=lambda x: (x['private'], x['path']))
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Escrever cabeçalho
                writer.writerow(['Caminho', 'URL Completa', 'Título', 'ID', 'ID Pai', 'Tipo'])
                
                # Escrever dados
                for page in sorted_pages:
                    writer.writerow([
                        page['path'],
                        page['url'],
                        page['title'],
                        page['id'],
                        page['parent_id'],
                        'Privada' if page['private'] else 'Pública'
                    ])
            
            self.logger.success(f"Arquivo CSV salvo com sucesso: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar CSV: {str(e)}")
            return False