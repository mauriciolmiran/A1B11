import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from concurrent.futures import ThreadPoolExecutor

SUDAN_ASNS = {
    "15706": "Sudatel (Sudani)",
    "36998": "Zain Sudan",
    "36972": "MTN Sudan",
    "33788": "Canar Telecom"
}

BASE_URL = "https://stat.ripe.net/data"

EVENTS = [
    # 2023
    {"date": "2023-04-15", "title": "Eclodir da Guerra", "period": "2023"},
    {"date": "2023-04-16", "title": "Ordem Desligamento MTN", "period": "2023"},
    {"date": "2023-04-23", "title": "Danos Geradores / Fibra", "period": "2023"},
    # 2024
    {"date": "2024-02-02", "title": "RSF Invasão Data Center Zain", "period": "2024"},
    {"date": "2024-02-05", "title": "Desligamento MTN", "period": "2024"},
    {"date": "2024-02-07", "title": "Apagão Nacional (>99%)", "period": "2024"},
    {"date": "2024-03-05", "title": "Migração para Port Sudan", "period": "2024"}
]

def fetch_updates_chunk(asn, start_str, end_str):
    url = f"{BASE_URL}/bgp-update-activity/data.json"
    try:
        r = requests.get(url, params={'resource': f'AS{asn}', 'starttime': start_str, 'endtime': end_str}, timeout=10)
        if r.status_code == 200:
            return r.json().get('data', {}).get('updates', [])
    except Exception as e:
        pass
    return []

def fetch_routing_history(asn, start_str, end_str):
    url = f"{BASE_URL}/routing-history/data.json"
    try:
        r = requests.get(url, params={'resource': f'AS{asn}', 'starttime': f"{start_str}T00:00:00", 'endtime': f"{end_str}T23:59:59"}, timeout=15)
        if r.status_code == 200:
            by_origin = r.json().get('data', {}).get('by_origin', [])
            if by_origin:
                prefixes = by_origin[0].get('prefixes', [])
                daily_counts = {}
                for p in prefixes:
                    for t in p.get('timelines', []):
                        st = t.get('starttime', '')[:10]
                        peers = t.get('full_peers_seeing', 0)
                        if peers > 10:
                            daily_counts[st] = daily_counts.get(st, 0) + 1
                return daily_counts
    except Exception as e:
        pass
    return {}

def process_asn_period(asn, start_date, end_date):
    # Fetch updates in 14-day chunks in parallel
    dates = pd.date_range(start_date, end_date, freq='14D')
    if dates[-1] < pd.Timestamp(end_date):
        dates = dates.append(pd.DatetimeIndex([end_date]))
        
    tasks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for i in range(len(dates)-1):
            s_str = dates[i].strftime('%Y-%m-%dT00:00:00')
            e_str = dates[i+1].strftime('%Y-%m-%dT00:00:00')
            tasks.append(executor.submit(fetch_updates_chunk, asn, s_str, e_str))
        hist_task = executor.submit(fetch_routing_history, asn, start_date, end_date)
        
    all_updates = []
    for t in tasks:
        all_updates.extend(t.result())
        
    hist_dict = hist_task.result()
    
    rec_up = [{'date': u['starttime'][:10], 'announcements': u.get('announcements', 0)} for u in all_updates]
    df_up = pd.DataFrame(rec_up)
    if not df_up.empty:
        df_up['date'] = pd.to_datetime(df_up['date'])
        df_up = df_up.drop_duplicates(subset=['date'])
        
    df_hist = pd.DataFrame(list(hist_dict.items()), columns=['date', 'visible_prefixes'])
    if not df_hist.empty:
        df_hist['date'] = pd.to_datetime(df_hist['date'])
        
    if not df_up.empty and not df_hist.empty:
        df_res = pd.merge(df_up, df_hist, on='date', how='outer').sort_values('date').fillna(0)
    elif not df_up.empty:
        df_res = df_up
        df_res['visible_prefixes'] = 0
    elif not df_hist.empty:
        df_res = df_hist
        df_res['announcements'] = 0
    else:
        df_res = pd.DataFrame()
        
    return df_res

def run():
    print("=== Executando Coleta Rápida em Paralelo e Plotagem Cruzada ===")
    periods = [
        {"tag": "2023", "title": "Eclodir do Conflito Militar (Abril - Maio 2023)", "start": "2023-04-01", "end": "2023-05-31"},
        {"tag": "2024", "title": "O Apagão Total de Cartum e Migração para Port Sudan (Jan - Mar 2024)", "start": "2024-01-20", "end": "2024-03-31"}
    ]
    
    colors = {
        "15706": "#1f77b4", # Sudatel
        "36998": "#2ca02c", # Zain
        "36972": "#ff7f0e", # MTN
        "33788": "#9467bd"  # Canar
    }
    
    os.makedirs("graphs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    for p in periods:
        print(f"\nProcessando Período: {p['title']}...")
        asn_data = {}
        for asn in SUDAN_ASNS.keys():
            print(f"Coletando AS{asn}...")
            df = process_asn_period(asn, p['start'], p['end'])
            asn_data[asn] = df
            if not df.empty:
                df_save = df.copy()
                df_save['date'] = df_save['date'].dt.strftime('%Y-%m-%d')
                df_save.to_json(f"data/fast_cross_AS{asn}_{p['tag']}.json", orient='records', indent=4)
                
        # Plotting
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True)
        
        # Upper subplot: Visible Prefixes
        for asn, name in SUDAN_ASNS.items():
            df = asn_data.get(asn, pd.DataFrame())
            if not df.empty and 'visible_prefixes' in df.columns:
                ax1.plot(df['date'], df['visible_prefixes'], label=f"AS{asn} - {name}", color=colors[asn], linewidth=2.2)
                
        ax1.set_title(f"Impacto no Plano de Controle BGP: {p['title']}\nPrefixos IP Visíveis Globalmente", fontsize=13, fontweight='bold', pad=10)
        ax1.set_ylabel("Prefixos Visíveis", fontsize=11, fontweight='bold')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(loc='upper right', fontsize=10)
        
        # Lower subplot: BGP Updates
        for asn, name in SUDAN_ASNS.items():
            df = asn_data.get(asn, pd.DataFrame())
            if not df.empty and 'announcements' in df.columns:
                ax2.plot(df['date'], df['announcements'], label=f"AS{asn} - {name}", color=colors[asn], linewidth=1.8, alpha=0.85)
                
        ax2.set_title("Atividade Diária de Anúncios BGP (Instabilidade / Route Flapping)", fontsize=12, fontweight='bold')
        ax2.set_xlabel("Data", fontsize=11, fontweight='bold')
        ax2.set_ylabel("BGP Updates / Dia", fontsize=11, fontweight='bold')
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(loc='upper right', fontsize=10)
        
        # Annotate Events
        period_events = [e for e in EVENTS if e['period'] == p['tag']]
        y_max1 = ax1.get_ylim()[1] if ax1.get_ylim()[1] > 0 else 100
        
        for idx, ev in enumerate(period_events):
            ev_date = pd.to_datetime(ev['date'])
            ax1.axvline(x=ev_date, color='#d62728', linestyle=':', linewidth=2, alpha=0.85)
            ax2.axvline(x=ev_date, color='#d62728', linestyle=':', linewidth=2, alpha=0.85)
            
            y_pos = y_max1 * (0.78 if idx % 2 == 0 else 0.42)
            ax1.annotate(
                f"[{ev['title']}]\n{ev['date']}",
                xy=(ev_date, y_max1 * 0.7),
                xytext=(ev_date, y_pos),
                arrowprops=dict(facecolor='#d62728', shrink=0.05, width=1.5, headwidth=5),
                fontsize=8.5,
                fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", fc="#fff1f0", ec="#d62728", lw=1.5),
                ha='center'
            )

        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%b'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        out_png = os.path.join("graphs", f"cross_analysis_{p['tag']}.png")
        plt.savefig(out_png, dpi=300)
        plt.close()
        print(f"Gráfico salvo em: {out_png}")

if __name__ == "__main__":
    run()
