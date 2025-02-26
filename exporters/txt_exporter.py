# -*- coding: utf-8 -*-
"""
Exportador TXT

Este módulo implementa a funcionalidade de exportação de URLs para arquivos de texto.

Uso:
    from exporters.txt_exporter import TXTExporter
    
    exporter = TXTExporter(logger)
    await exporter.export(pages, output_file)
"""

from typing import List, Dict, Any
from utils.logger import Logger

class TXTExporter:
    """Exportador de URLs para arquivos de texto."""
    
    def __init__(self, logger: Logger):
        """
        Inicializa o exportador TXT.
        
        Args:
            logger: Logger para registrar operações
        """
        self.logger = logger
    
    async def export(self, pages: List[Dict[str, Any]], output_file: str) -> bool:
        """
        Exporta uma lista de URLs para um arquivo de texto.
        
        Args:
            pages: Lista de páginas para exportar
            output_file: Caminho do arquivo TXT de saída
            
        Returns:
            Boolean indicando sucesso ou falha
        """
        self.logger.info(f"Salvando URLs em arquivo de texto: {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as txtfile:
                # Extrair e ordenar as URLs
                urls = sorted([page['url'] for page in pages])
                
                # Escrever URLs (uma por linha), removendo a barra no final, se existir
                for url in urls:
                    # Remover a barra final se a URL terminar com /
                    if url.endswith('/'):
                        url = url[:-1]
                    txtfile.write(f"{url}\n")
            
            self.logger.success(f"Arquivo TXT com {len(urls)} URLs salvo com sucesso: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivo TXT: {str(e)}")
            return False