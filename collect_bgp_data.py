import os
import json
import requests
import datetime

# Dicionário de ASNs importantes do Sudão
SUDAN_ASNS = {
    "15706": "Sudatel (Sudani)",
    "36998": "Zain Sudan",
    "36972": "MTN Sudan",
    "33788": "Canar Telecom"
}

BASE_URL = "https://stat.ripe.net/data"

def get_routing_status(asn):
    """
    Busca o status de roteamento atual do ASN.
    """
    url = f"{BASE_URL}/routing-status/data.json"
    params = {"resource": f"AS{asn}"}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()["data"]
    except Exception as e:
        print(f"Erro ao buscar status para AS{asn}: {e}")
        return None

def get_bgp_update_activity(asn, starttime, endtime):
    """
    Busca a contagem de atualizações BGP (announcements e withdrawals)
    agregadas ao longo de um período.
    
    Timestamps devem ser no formato ISO (ex: YYYY-MM-DDTHH:MM:SS)
    """
    url = f"{BASE_URL}/bgp-update-activity/data.json"
    params = {
        "resource": f"AS{asn}",
        "starttime": starttime,
        "endtime": endtime
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()["data"]
    except Exception as e:
        print(f"Erro ao buscar atividade BGP para AS{asn}: {e}")
        return None

def save_data(data, filename):
    """
    Salva os dados coletados em formato JSON formatado.
    """
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Dados salvos com sucesso em: {filepath}")

def run_collection():
    print("=== Iniciando Coleta de Dados BGP do Sudão ===")
    
    # 1. Obter Status de Roteamento Atual
    print("\n--- 1. Obtendo Status Atual de Roteamento ---")
    for asn, name in SUDAN_ASNS.items():
        print(f"Coletando status para {name} (AS{asn})...")
        status = get_routing_status(asn)
        if status:
            save_data(status, f"status_AS{asn}.json")
            
    # 2. Obter Dados de Atualizações BGP para Períodos Críticos da Guerra
    # Período 1: O Eclodir da Guerra (Abril a Maio de 2023)
    # Período 2: O Grande Apagão de Cartum (Fevereiro a Março de 2024)
    print("\n--- 2. Obtendo Histórico de Atividade BGP (Updates) ---")
    periodos = [
        {
            "nome": "eclodir_guerra_2023",
            "start": "2023-04-01T00:00:00",
            "end": "2023-05-31T23:59:59"
        },
        {
            "nome": "apagao_cartum_2024",
            "start": "2024-02-01T00:00:00",
            "end": "2024-03-31T23:59:59"
        }
    ]
    
    for periodo in periodos:
        print(f"\nColetando período: {periodo['nome']} ({periodo['start']} até {periodo['end']})...")
        for asn, name in SUDAN_ASNS.items():
            print(f"Coletando atividade BGP para {name} (AS{asn})...")
            activity = get_bgp_update_activity(asn, periodo["start"], periodo["end"])
            if activity:
                save_data(activity, f"activity_{periodo['nome']}_AS{asn}.json")

    print("\n=== Coleta Concluída! ===")
    print("Os dados estão salvos no diretório './data'. Você pode usar estes arquivos JSON")
    print("para gerar tabelas CSV ou plotar gráficos de announcements/withdrawals no tempo.")

if __name__ == "__main__":
    run_collection()
