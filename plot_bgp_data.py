import os
import json
import glob
import datetime

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

def process_and_plot():
    if not HAS_LIBS:
        print("Aviso: pandas e matplotlib não estão instalados.")
        print("Execute: pip install pandas matplotlib")
        print("Para gerar os gráficos automaticamente a partir dos JSONs.")
        return

    data_dir = "data"
    files = glob.glob(os.path.join(data_dir, "activity_*.json"))
    
    if not files:
        print("Nenhum dado de atividade BGP encontrado no diretório './data'.")
        print("Por favor, execute o script 'collect_bgp_data.py' primeiro.")
        return

    print("=== Processando dados e gerando gráficos ===")
    
    for file_path in files:
        filename = os.path.basename(file_path)
        # Nome do arquivo formato: activity_{periodo}_AS{asn}.json
        parts = filename.replace("activity_", "").replace(".json", "").split("_AS")
        if len(parts) != 2:
            continue
        periodo, asn = parts
        
        print(f"Processando {filename} (AS{asn} - Período: {periodo})...")
        
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        # O RIPE Stat retorna os dados na chave 'updates' ou 'activity'
        # Vamos verificar a estrutura da resposta do bgp-update-activity
        # Estrutura típica: "data": { "updates": [ { "announcements": X, "withdrawals": Y, "starttime": Z, ... } ] }
        updates = raw_data.get("updates", [])
        if not updates:
            print(f"Sem dados de atualizações em {filename}")
            continue
            
        # Carregar em DataFrame
        df = pd.DataFrame(updates)
        
        # Converter timestamps para datetime
        # RIPE Stat pode retornar 'starttime' como string ou unix timestamp
        # Vamos tentar converter de forma genérica
        df['datetime'] = pd.to_datetime(df['starttime'])
        
        # Ordenar por data
        df = df.sort_values('datetime')
        
        # Criar pasta para os gráficos
        os.makedirs("graphs", exist_ok=True)
        
        # Plotar
        plt.figure(figsize=(12, 6))
        plt.plot(df['datetime'], df['announcements'], label='Anúncios (Announcements)', color='#1f77b4', alpha=0.8)
        
        # O RIPE Stat retorna null para withdrawals em consultas de ASN. Plotamos apenas se houver dados válidos.
        if 'withdrawals' in df.columns and df['withdrawals'].notna().any() and (df['withdrawals'] > 0).any():
            plt.plot(df['datetime'], df['withdrawals'], label='Retiradas (Withdrawals)', color='#d62728', alpha=0.8)
        
        plt.title(f"Atividade BGP - AS{asn} durante o período: {periodo.replace('_', ' ').title()}", fontsize=14, fontweight='bold')
        plt.xlabel("Tempo", fontsize=12)
        plt.ylabel("Contagem de Updates BGP", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize=11)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        graph_path = os.path.join("graphs", f"chart_{periodo}_AS{asn}.png")
        plt.savefig(graph_path, dpi=300)
        plt.close()
        print(f"Gráfico salvo com sucesso em: {graph_path}")

    print("\n=== Processamento Concluído! ===")
    print("Verifique a pasta './graphs' para visualizar os gráficos gerados.")

if __name__ == "__main__":
    process_and_plot()
