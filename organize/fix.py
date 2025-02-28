import pandas as pd

def organizar_planilha(caminho_arquivo, caminho_saida):
    """
    Organiza uma planilha de URLs, associando corretamente os links 'Para' com seus respectivos 'De',
    mantendo a estrutura e ordem original da coluna 'De'.
    
    Args:
        caminho_arquivo: Caminho do arquivo Excel original
        caminho_saida: Caminho para salvar o arquivo Excel organizado
    """
    # Ler a planilha
    df = pd.read_excel(caminho_arquivo)
    
    # Função para extrair a parte final do link (após a última "/")
    def extract_path(url):
        if isinstance(url, str) and "/" in url:
            return url.rstrip("/").split("/")[-1]  # Pega a última parte do link
        return None
    
    # Criar colunas auxiliares com os trechos comparáveis
    df["De_Trecho"] = df["De"].apply(extract_path)
    df["Para_Trecho"] = df["Para"].apply(extract_path)
    
    # Criar um dicionário para mapear "De_Trecho" ao link completo "Para"
    # Vamos mapear de "Para_Trecho" para "Para" para obter o link completo correto
    para_mapping = df.dropna(subset=["Para_Trecho", "Para"]).set_index("Para_Trecho")["Para"].to_dict()
    
    # Criar uma nova coluna "Para_Correto" baseada no "De_Trecho"
    df["Para_Correto"] = df["De_Trecho"].map(para_mapping)
    
    # Manter a estrutura original da coluna "De", substituindo apenas a coluna "Para"
    df_resultado = df[["De", "Para_Correto"]].rename(columns={"Para_Correto": "Para"})
    
    # Salvar a planilha organizada
    df_resultado.to_excel(caminho_saida, index=False)
    
    print(f"Planilha organizada salva em: {caminho_saida}")
    
    return df_resultado

# Exemplo de uso
if __name__ == "__main__":
    caminho_arquivo = "SEJUS_RESULT.xlsx"
    caminho_saida = "SEJUS_RESULT_ORGANIZADO.xlsx"
    
    df_resultado = organizar_planilha(caminho_arquivo, caminho_saida)
    
    # Exibir as primeiras linhas do resultado
    print("\nPrimeiras linhas do resultado:")
    print(df_resultado.head())