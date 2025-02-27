# Liferay URL Extractor

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0.0-blue.svg" alt="Version 3.0.0">
  <img src="https://img.shields.io/badge/python-3.8+-brightgreen.svg" alt="Python 3.8+">
</p>

Uma ferramenta robusta para extrair e mapear todas as URLs de um portal Liferay, gerando relatórios detalhados em diferentes formatos e visualizando a estrutura hierárquica do site.

## ✨ Características

- **Extração Completa**: Recupera todas as páginas públicas e privadas do Liferay
- **Processamento Otimizado**: Execução assíncrona para extrações mais rápidas
- **Sistema de Cache**: Reduz a carga no servidor e acelera extrações repetidas
- **Retomada Inteligente**: Capacidade de continuar extrações interrompidas
- **Relatórios Múltiplos**:
  - Arquivo CSV com informações detalhadas de cada página
  - Lista de URLs em formato texto simples
  - Mapa visual do site em HTML interativo
- **Interface Rica**: Barra de progresso em tempo real e relatórios formatados
- **Estrutura Modular**: Código bem organizado e fácil de manter

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Acesso a um portal Liferay
- Credenciais com permissões adequadas

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seuusuario/liferay-url-extractor.git
cd liferay-url-extractor
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o arquivo `.env` com suas credenciais:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## ⚙️ Configuração

Edite o arquivo `.env` com os seguintes parâmetros:

```
# Conexão com o Liferay
LIFERAY_URL=https://seu-portal-liferay.com
EMAIL=seu-email@exemplo.com
PASSWORD=sua-senha
GROUP_ID=123456

# Arquivos de saída
OUTPUT_FILE=all_liferay_urls.csv
OUTPUT_TXT=all_urls.txt
SITE_MAP_FILE=site_structure.html

# Configurações de performance
MAX_CONCURRENT_REQUESTS=10
CACHE_DIR=.cache
CACHE_TTL=24
RESUME_EXTRACTION=True
```

## 🔧 Utilização

Execute a ferramenta com o seguinte comando:

```bash
python main.py
```

O processo extrairá todas as URLs do portal Liferay configurado e gerará:

1. Um arquivo CSV com detalhes de todas as páginas
2. Um arquivo de texto com as URLs (uma por linha)
3. Um mapa visual do site em HTML

## 📁 Estrutura do Projeto

```
liferay_url_extractor/
├── config/               # Configurações do aplicativo
├── core/                 # Componentes principais 
├── utils/                # Utilitários e helpers
├── exporters/            # Exportadores para diferentes formatos
├── models/               # Modelos de dados
├── main.py               # Ponto de entrada do aplicativo
└── requirements.txt      # Dependências do projeto
```

## 📊 Relatório de Estatísticas

Ao final da execução, a ferramenta exibe um relatório detalhado:

- Número total de páginas extraídas
- Distribuição entre páginas públicas e privadas
- Profundidade máxima da estrutura do site
- Estatísticas de requisições e cache
- Tempo de execução e desempenho

## 🔍 Mapa do Site

O mapa visual do site gerado fornece:

- Visualização hierárquica completa da estrutura
- Navegação interativa com expansão/contração de seções
- Links diretos para todas as páginas
- Estatísticas de distribuição e profundidade

## 🛠️ Desenvolvimento

### Componentes Modulares

O sistema utiliza uma arquitetura modular para facilitar extensões:

- **Extrator**: Coordena todo o processo de extração
- **Gerenciador de Sessão**: Cuida da comunicação com a API do Liferay
- **Gerenciador de Cache**: Otimiza requisições repetidas
- **Exportadores**: Geram diferentes formatos de saída 
- **Logger**: Fornece feedback consistente durante a execução

### Extendendo Funcionalidades

Para adicionar novos formatos de exportação:

1. Crie uma nova classe no diretório `exporters/`
2. Implemente a interface com o método `export()`
3. Registre o novo exportador no método `save_results()` do extrator
