# -*- coding: utf-8 -*-
"""
Funções Auxiliares 

Este módulo fornece funções auxiliares genéricas usadas em diferentes partes do projeto.

Uso:
    from utils.helpers import save_state, load_state
    
    # Salvar estado
    save_state(state_file, data)
    
    # Carregar estado
    data = load_state(state_file)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Set, Optional, List

def save_state(file_path: Path, all_pages: List[Dict[str, Any]], 
              processed_layouts: Set[str], stats: Dict[str, Any], 
              site_structure: Dict[str, Any]) -> bool:
    """
    Salva o estado atual de extração em um arquivo JSON.
    
    Args:
        file_path: Caminho do arquivo de estado
        all_pages: Lista de páginas extraídas
        processed_layouts: Conjunto de layouts já processados
        stats: Estatísticas de execução
        site_structure: Estrutura hierárquica do site
        
    Returns:
        Boolean indicando sucesso ou falha na operação
    """
    try:
        state = {
            'all_pages': all_pages,
            'processed_layouts': list(processed_layouts),  # Converter set para list
            'stats': stats,
            'site_structure': site_structure
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception:
        return False

def load_state(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Carrega o estado anterior de um arquivo JSON.
    
    Args:
        file_path: Caminho do arquivo de estado
        
    Returns:
        Dicionário com o estado carregado, ou None em caso de erro
    """
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state
    except Exception:
        return None

def generate_cache_key(base_url: str, group_id: str) -> str:
    """
    Gera uma chave única de cache baseada nos parâmetros de conexão.
    
    Args:
        base_url: URL base do Liferay
        group_id: ID do grupo/site
        
    Returns:
        String com hash MD5 para usar como identificador de cache
    """
    key_data = f"{base_url}:{group_id}"
    return hashlib.md5(key_data.encode()).hexdigest()

def convert_processed_layouts(layouts_list: List[str]) -> Set[str]:
    """
    Converte uma lista de layouts processados para um conjunto (set).
    
    Args:
        layouts_list: Lista de strings representando layouts processados
        
    Returns:
        Conjunto (set) de layouts processados
    """
    return set(layouts_list)