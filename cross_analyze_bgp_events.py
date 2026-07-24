import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# Configurações de ASNs do Sudão
SUDAN_ASNS = {
    "15706": "Sudatel (Sudani)",
    "36998": "Zain Sudan",
    "36972": "MTN Sudan",
    "33788": "Canar Telecom"
}

BASE_URL = "https://stat.ripe.net/data"

# Cronologia Histórica de Conflitos e Apagões no Sudão (Fontes: NetBlocks, IODA, Cloudflare Radar, Access Now, Reuters)
EVENTS = [
    # Período 1: Eclodir da Guerra (2023)
    {
        "date": "2023-04-15",
        "title": "Eclodir da Guerra Civil",
        "desc": "Conflito SAF vs. RSF eclode em Cartum; combates ao redor do aeroporto e Palácio.",
        "period": "2023"
    },
    {
        "date": "2023-04-16",
        "title": "Ordem de Desligamento da MTN",
        "desc": "Regulador NTC ordena desligamento da MTN (AS36972); reestabelecido sob pressão.",
        "period": "2023"
    },
    {
        "date": "2023-04-23",
        "title": "Colapso de Energia e Fibra",
        "desc": "Ataques e falta de combustível causam quedas severas na Sudatel e Zain.",
        "period": "2023"
    },
    
    # Período 2: Apagão Total de Cartum e Port Sudan (2024)
    {
        "date": "2024-02-02",
        "title": "RSF Invasão Data Center Zain",
        "desc": "RSF desliga data centers da Zain em Cartum após corte de rede em Darfur.",
        "period": "2024"
    },
    {
        "date": "2024-02-05",
        "title": "Desligamento MTN",
        "desc": "MTN Sudan é forçada a desligar switches em Cartum.",
        "period": "2024"
    },
    {
        "date": "2024-02-07",
        "title": "Apagão Nacional Total (Sudatel/Canar)",
        "desc": "Sudatel e Canar caem. Sudão fica com >99% de perda de conectividade global.",
        "period": "2024"
    },
    {
        "date": "2024-03-05",
        "title": "Migração para Port Sudan",
        "desc": "Sudatel reestabelece roteamento core via novos data centers em Port Sudan.",
        "period": "2024"
    }
]

def fetch_daily_bgp_updates(asn, start_date, end_date):
    """Busca o número diário de BGP Updates do RIPE Stat dividindo em intervalos curtos."""
    url = f"{BASE_URL}/bgp-update-activity/data.json"
    dates = pd.date_range(start_date, end_date, freq='14D')
    if dates[-1] < pd.Timestamp(end_date):
        dates = dates.append(pd.DatetimeIndex([end_date]))
        
    records = []
    for i in range(len(dates)-1):
        s_str = dates[i].strftime('%Y-%m-%dT00:00:00')
        e_str = dates[i+1].strftime('%Y-%m-%dT00:00:00')
        try:
            r = requests.get(url, params={'resource': f'AS{asn}', 'starttime': s_str, 'endtime': e_str}, timeout=15)
            r.raise_for_status()
            updates = r.json().get('data', {}).get('updates', [])
            for u in updates:
                records.append({
                    'date': u['starttime'][:10],
                    'announcements': u.get('announcements', 0)
                })
        except Exception as e:
            print(f"Erro ao buscar BGP updates para AS{asn} entre {s_str} e {e_str}: {e}")
            
    df = pd.DataFrame(records)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df = df.drop_duplicates(subset=['date']).sort_values('date')
    return df

def fetch_routing_history(asn, start_date, end_date):
    """Busca o histórico de contagem de prefixos visíveis do RIPE Stat."""
    url = f"{BASE_URL}/routing-history/data.json"
    try:
        r = requests.get(url, params={'resource': f'AS{asn}', 'starttime': f"{start_date}T00:00:00", 'endtime': f"{end_date}T23:59:59"}, timeout=25)
        r.raise_for_status()
        by_origin = r.json().get('data', {}).get('by_origin', [])
        if not by_origin:
            return pd.DataFrame()
        
        prefixes = by_origin[0].get('prefixes', [])
        daily_counts = {}
        for p in prefixes:
            for t in p.get('timelines', []):
                st = t.get('starttime', '')[:10]
                peers = t.get('full_peers_seeing', 0)
                if peers > 10:  # Considerando prefixos vistos por múltiplos coletores RIS
                    daily_counts[st] = daily_counts.get(st, 0) + 1
                    
        df = pd.DataFrame(list(daily_counts.items()), columns=['date', 'visible_prefixes'])
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        return df
    except Exception as e:
        print(f"Erro ao buscar routing-history para AS{asn}: {e}")
        return pd.DataFrame()

def run_cross_analysis():
    print("=== Coletando Dados de Alta Resolução e Cruzando com Eventos Históricos ===")
    
    periods = [
        {"name": "Eclodir da Guerra (2023)", "start": "2023-04-01", "end": "2023-05-31", "period_tag": "2023"},
        {"name": "Grande Apagão de Cartum e Port Sudan (2024)", "start": "2024-01-20", "end": "2024-03-31", "period_tag": "2024"}
    ]
    
    all_data = {}
    
    for p in periods:
        print(f"\n--- Período: {p['name']} ---")
        all_data[p['period_tag']] = {}
        for asn, name in SUDAN_ASNS.items():
            print(f"Buscando dados para {name} (AS{asn})...")
            df_up = fetch_daily_bgp_updates(asn, p['start'], p['end'])
            df_hist = fetch_routing_history(asn, p['start'], p['end'])
            
            # Merge
            if not df_up.empty and not df_hist.empty:
                df_merged = pd.merge(df_up, df_hist, on='date', how='outer').sort_values('date').fillna(0)
            elif not df_up.empty:
                df_merged = df_up
                df_merged['visible_prefixes'] = 0
            else:
                df_merged = df_hist
                if not df_merged.empty:
                    df_merged['announcements'] = 0
                
            all_data[p['period_tag']][asn] = df_merged
            
            # Salvar JSON formatado
            if not df_merged.empty:
                save_df = df_merged.copy()
                save_df['date'] = save_df['date'].dt.strftime('%Y-%m-%d')
                os.makedirs("data", exist_ok=True)
                save_df.to_json(f"data/daily_cross_AS{asn}_{p['period_tag']}.json", orient='records', indent=4)

    # Gerar Gráficos Cruzados com Anotações Históricas
    plot_cross_charts(all_data)

def plot_cross_charts(all_data):
    os.makedirs("graphs", exist_ok=True)
    
    period_labels = {
        "2023": ("Eclodir do Conflito Militar no Sudão (Abril - Maio 2023)", "2023-04-01", "2023-05-31"),
        "2024": ("O Apagão Total de Cartum e Reabertura em Port Sudan (Jan - Mar 2024)", "2024-01-20", "2024-03-31")
    }
    
    colors = {
        "15706": "#1f77b4", # Sudatel - Azul
        "36998": "#2ca02c", # Zain - Verde
        "36972": "#ff7f0e", # MTN - Laranja
        "33788": "#9467bd"  # Canar - Roxo
    }
    
    for tag, (title, s_date, e_date) in period_labels.items():
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        
        # 1. Gráfico Superior: Prefixos Visíveis no Roteamento Global
        for asn, name in SUDAN_ASNS.items():
            df = all_data[tag].get(asn, pd.DataFrame())
            if not df.empty and 'visible_prefixes' in df.columns and (df['visible_prefixes'] > 0).any():
                ax1.plot(df['date'], df['visible_prefixes'], label=f"AS{asn} - {name}", color=colors[asn], linewidth=2.2)
                
        ax1.set_title(f"Impacto no Plano de Controle BGP: {title}\nPrefixos IP Visíveis Globalmente", fontsize=13, fontweight='bold', pad=12)
        ax1.set_ylabel("Quantidade de Prefixos Visíveis", fontsize=11, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right', fontsize=10, framealpha=0.9)
        
        # 2. Gráfico Inferior: Volume Diário de Anúncios BGP (BGP Flapping / Updates)
        for asn, name in SUDAN_ASNS.items():
            df = all_data[tag].get(asn, pd.DataFrame())
            if not df.empty and 'announcements' in df.columns:
                ax2.plot(df['date'], df['announcements'], label=f"AS{asn} - {name}", color=colors[asn], linewidth=1.8, alpha=0.85)
                
        ax2.set_title("Atividade Diária de Anúncios BGP (Instabilidade / Route Flapping)", fontsize=12, fontweight='bold')
        ax2.set_xlabel("Data", fontsize=11, fontweight='bold')
        ax2.set_ylabel("BGP Updates / Anúncios por Dia", fontsize=11, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)
        
        # Adicionar Linhas Verticais e Callouts dos Eventos Históricos
        period_events = [e for e in EVENTS if e['period'] == tag]
        
        # Ajustar posições de texto para evitar sobreposição
        y_max1 = ax1.get_ylim()[1]
        y_max2 = ax2.get_ylim()[1]
        
        for idx, ev in enumerate(period_events):
            ev_date = pd.to_datetime(ev['date'])
            
            # Linhas verticais nos dois subplots
            ax1.axvline(x=ev_date, color='#d62728', linestyle=':', linewidth=2, alpha=0.85)
            ax2.axvline(x=ev_date, color='#d62728', linestyle=':', linewidth=2, alpha=0.85)
            
            # Rotular no ax1
            ax1.annotate(
                f"[{ev['title']}]\n{ev['date']}",
                xy=(ev_date, y_max1 * 0.75),
                xytext=(ev_date, y_max1 * (0.82 if idx % 2 == 0 else 0.45)),
                arrowprops=dict(facecolor='#d62728', shrink=0.05, width=1.5, headwidth=6),
                fontsize=9,
                fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="#fff1f0", ec="#d62728", lw=1.5),
                ha='center'
            )

        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%b'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = os.path.join("graphs", f"cross_analysis_{tag}.png")
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"Gráfico de cruzamento salvo com sucesso em: {output_path}")

if __name__ == "__main__":
    run_cross_analysis()
