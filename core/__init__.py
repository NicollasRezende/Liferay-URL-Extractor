# -*- coding: utf-8 -*-
"""
Pacote core do Liferay URL Extractor.

Este pacote contém os componentes principais da aplicação,
responsáveis pela lógica de negócio e funcionalidades centrais.
"""

from core.extractor import LiferayUrlExtractor
from core.cache import CacheManager
from core.session import SessionManager

__all__ = ['LiferayUrlExtractor', 'CacheManager', 'SessionManager']