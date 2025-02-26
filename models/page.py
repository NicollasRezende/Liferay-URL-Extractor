# -*- coding: utf-8 -*-
"""
Modelo de Página do Liferay

Define a estrutura de dados para representar páginas extraídas do Liferay,
facilitando o processamento consistente de informações em toda a aplicação.

Uso:
    from models.page import Page
    page = Page(id=1, path="/home", url="https://example.com/home", ...)
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Page:
    """
    Representa uma página do Liferay com suas propriedades.
    
    Attributes:
        id: ID da página no Liferay
        path: Caminho relativo da página
        url: URL completa da página
        title: Título da página
        parent_id: ID da página pai
        private: Flag indicando se a página é privada
    """
    id: int
    path: str
    url: str
    title: str
    parent_id: int
    private: bool
    
    @classmethod
    def from_json(cls, layout: Dict[str, Any], parent_url: str, is_private: bool, base_url: str) -> 'Page':
        """
        Cria uma instância de Page a partir de dados JSON do Liferay.
        
        Args:
            layout: Dados JSON do layout retornado pela API do Liferay
            parent_url: URL da página pai
            is_private: Flag indicando se a página é privada
            base_url: URL base do Liferay
            
        Returns:
            Uma nova instância da classe Page
        """
        from urllib.parse import urljoin
        
        layout_id = layout.get('layoutId', 0)
        friendly_url = layout.get('friendlyURL', '')
        layout_name = layout.get('name', '')
        
        # Remover barra inicial se necessário
        if friendly_url.startswith('/'):
            friendly_url = friendly_url[1:]
            
        # Construir o caminho completo para esta página
        full_path = f"{parent_url}/{friendly_url}" if parent_url else friendly_url
        
        # Criar URL completa
        complete_url = urljoin(base_url, full_path)
        
        # Remover a barra final se a URL terminar com /
        if complete_url.endswith('/'):
            complete_url = complete_url[:-1]
        
        return cls(
            id=layout_id,
            path=full_path,
            url=complete_url,
            title=layout_name,
            parent_id=layout.get('parentLayoutId', 0),
            private=is_private
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a página para um dicionário.
        
        Returns:
            Um dicionário com os atributos da página.
        """
        return {
            'id': self.id,
            'path': self.path,
            'url': self.url,
            'title': self.title,
            'parent_id': self.parent_id,
            'private': self.private
        }
    
    def get_display_type(self) -> str:
        """
        Retorna o tipo de página em formato legível.
        
        Returns:
            String "Privada" ou "Pública" dependendo do tipo da página.
        """
        return "Privada" if self.private else "Pública"