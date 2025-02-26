# -*- coding: utf-8 -*-
"""
Pacote de configurações do Liferay URL Extractor.

Este pacote contém módulos relacionados à configuração da aplicação,
como carregamento de variáveis de ambiente e definição de parâmetros.
"""

from config.settings import load_config, AppConfig

__all__ = ['load_config', 'AppConfig']