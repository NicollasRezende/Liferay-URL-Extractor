# -*- coding: utf-8 -*-
"""
Exportador de Mapa do Site

Este módulo implementa a funcionalidade de geração de um mapa visual do site
em formato HTML, exibindo a estrutura hierárquica das páginas do Liferay.

Uso:
    from exporters.sitemap_exporter import SitemapExporter
    
    exporter = SitemapExporter(logger, liferay_url)
    await exporter.export(site_structure, output_file)
"""

from urllib.parse import urljoin
from typing import Dict, Any
from utils.logger import Logger

class SitemapExporter:
    """Exportador de estrutura do site para HTML."""
    
    def __init__(self, logger: Logger, base_url: str):
        """
        Inicializa o exportador de mapa do site.
        
        Args:
            logger: Logger para registrar operações
            base_url: URL base do Liferay
        """
        self.logger = logger
        self.base_url = base_url
        self.total_public = 0
        self.total_private = 0
        self.max_depth = 0
    
    async def export(self, site_structure: Dict[str, Any], output_file: str) -> bool:
        """
        Gera um arquivo HTML com a estrutura visual do site.
        
        Args:
            site_structure: Dicionário com a estrutura hierárquica do site
            output_file: Caminho do arquivo HTML de saída
            
        Returns:
            Boolean indicando sucesso ou falha
        """
        self.logger.info(f"Gerando mapa visual do site: {output_file}")
        
        try:
            # Resetar contadores
            self.total_public = 0
            self.total_private = 0
            self.max_depth = 0
            
            # Criar HTML com visualização em árvore
            with open(output_file, 'w', encoding='utf-8') as f:
                # Escrever cabeçalho HTML com CSS e estrutura básica
                f.write(self._generate_html_header())
                
                # Seção Páginas Públicas
                f.write('''
    <div class="site-map">
        <div class="site-section">
            <h2>Páginas Públicas</h2>
            <div class="tree">
''')
                f.write(self._render_tree(site_structure.get('public', {}), is_private=False))
                f.write('''
            </div>
        </div>
''')

                # Seção Páginas Privadas
                f.write('''
        <div class="site-section">
            <h2>Páginas Privadas</h2>
            <div class="tree">
''')
                f.write(self._render_tree(site_structure.get('private', {}), is_private=True))
                f.write('''
            </div>
        </div>
    </div>
''')

                # JavaScript para as estatísticas e interatividade
                f.write(self._generate_html_footer())
            
            self.logger.success(f"Mapa do site gerado com sucesso: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar mapa do site: {str(e)}")
            return False
    
    def _render_tree(self, structure: Dict[str, Any], path_prefix: str = "", depth: int = 1, is_private: bool = False) -> str:
        """
        Renderiza recursivamente a estrutura do site em HTML.
        
        Args:
            structure: Dicionário com a estrutura do site
            path_prefix: Prefixo do caminho para URLs completas
            depth: Profundidade atual na árvore
            is_private: Flag indicando se é uma seção privada
            
        Returns:
            String com HTML da árvore de páginas
        """
        # Atualizar profundidade máxima
        self.max_depth = max(self.max_depth, depth)
        
        # Iniciar lista
        html = '<ul>\n'
        
        # Processar cada item na estrutura (ordenados alfabeticamente)
        for key, data in sorted(structure.items()):
            # Atualizar contadores
            if is_private:
                self.total_private += 1
            else:
                self.total_public += 1
                
            # Construir o caminho completo
            if path_prefix:
                full_path = f"{path_prefix}/{key}"
            else:
                full_path = key
                
            # Construir a URL completa
            url = urljoin(self.base_url, full_path)
            
            # Remover a barra final se a URL terminar com /
            if url.endswith('/'):
                url = url[:-1]
            
            # Verificar se tem filhos
            has_children = len(data.get('children', {})) > 0
            
            # Iniciar o item da lista
            html += '    <li>'
            
            # Toggle se tiver filhos
            if has_children:
                html += f'<span class="toggle" onclick="toggleSubtree(this);">[+]</span> '
                
            # Link para a página
            html += f'<a href="{url}" target="_blank">{data.get("title") or key}</a> '
            
            # Informações adicionais
            html += f'<span class="info">(ID: {data.get("id", "N/A")})</span>'
            
            # Renderizar filhos recursivamente
            if has_children:
                html += f'\n    <div class="subtree hidden">'
                html += self._render_tree(data.get('children', {}), full_path, depth + 1, is_private)
                html += '    </div>'
                
            html += '</li>\n'
            
        html += '</ul>\n'
        return html
    
    def _generate_html_header(self) -> str:
        """
        Gera o cabeçalho HTML com estilos CSS.
        
        Returns:
            String com cabeçalho HTML e CSS
        """
        return '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapa do Site - Estrutura Hierárquica</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .site-map {
            margin: 20px 0;
        }
        .site-section {
            margin-bottom: 30px;
        }
        .site-section h2 {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            color: #2980b9;
        }
        .tree {
            margin-left: 20px;
        }
        .tree ul {
            list-style-type: none;
            padding-left: 20px;
        }
        .tree li {
            margin: 5px 0;
            position: relative;
        }
        .tree li::before {
            content: "├─";
            position: absolute;
            left: -20px;
            color: #95a5a6;
        }
        .tree li:last-child::before {
            content: "└─";
        }
        .tree a {
            text-decoration: none;
            color: #3498db;
            padding: 2px 5px;
            border-radius: 3px;
            transition: background-color 0.2s;
        }
        .tree a:hover {
            background-color: #eaf2f8;
            text-decoration: underline;
        }
        .info {
            font-size: 0.8em;
            color: #7f8c8d;
            margin-left: 10px;
        }
        .toggle {
            cursor: pointer;
            user-select: none;
            color: #7f8c8d;
            margin-right: 5px;
        }
        .hidden {
            display: none;
        }
        .summary {
            background-color: #f0f0f0;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
        }
        .summary div {
            text-align: center;
        }
        .summary .count {
            font-size: 1.8em;
            font-weight: bold;
            color: #3498db;
        }
        .summary .label {
            font-size: 0.9em;
            color: #7f8c8d;
        }
        
        /* Toggle button */
        .expand-all, .collapse-all {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .expand-all:hover, .collapse-all:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    <h1>Mapa do Site - Estrutura Hierárquica</h1>
    
    <div class="summary">
        <div>
            <div class="count" id="total-pages">0</div>
            <div class="label">Total de Páginas</div>
        </div>
        <div>
            <div class="count" id="public-pages">0</div>
            <div class="label">Páginas Públicas</div>
        </div>
        <div>
            <div class="count" id="private-pages">0</div>
            <div class="label">Páginas Privadas</div>
        </div>
        <div>
            <div class="count" id="max-depth">0</div>
            <div class="label">Profundidade Máxima</div>
        </div>
    </div>
    
    <div>
        <button class="expand-all" onclick="expandAll()">Expandir Tudo</button>
        <button class="collapse-all" onclick="collapseAll()">Colapsar Tudo</button>
    </div>
'''
    
    def _generate_html_footer(self) -> str:
        """
        Gera o rodapé HTML com JavaScript para interatividade.
        
        Returns:
            String com rodapé HTML e JavaScript
        """
        return f'''
    <script>
        // Atualizar estatísticas
        document.getElementById('total-pages').textContent = '{self.total_public + self.total_private}';
        document.getElementById('public-pages').textContent = '{self.total_public}';
        document.getElementById('private-pages').textContent = '{self.total_private}';
        document.getElementById('max-depth').textContent = '{self.max_depth}';
        
        // Função para expandir todos os nós
        function expandAll() {{
            var subtrees = document.querySelectorAll('.subtree');
            var toggles = document.querySelectorAll('.toggle');
            
            subtrees.forEach(function(el) {{
                el.classList.remove('hidden');
            }});
            
            toggles.forEach(function(el) {{
                el.textContent = '[-]';
            }});
        }}
        
        // Função para colapsar todos os nós
        function collapseAll() {{
            var subtrees = document.querySelectorAll('.subtree');
            var toggles = document.querySelectorAll('.toggle');
            
            subtrees.forEach(function(el) {{
                el.classList.add('hidden');
            }});
            
            toggles.forEach(function(el) {{
                el.textContent = '[+]';
            }});
        }}
        
        // Função para alternar a visibilidade de uma subárvore
        function toggleSubtree(element) {{
            var subtree = element.parentElement.querySelector('.subtree');
            
            if (subtree.classList.contains('hidden')) {{
                subtree.classList.remove('hidden');
                element.textContent = '[-]';
            }} else {{
                subtree.classList.add('hidden');
                element.textContent = '[+]';
            }}
        }}
    </script>
</body>
</html>
'''