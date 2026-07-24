# Análise de Roteamento BGP - Guerra do Sudão (2023-2024)

Este repositório contém scripts em Python desenvolvidos para coletar, processar e visualizar dados do plano de controle BGP (Border Gateway Protocol) de quatro Sistemas Autônomos (ASes) críticos do Sudão durante os conflitos de 2023 e 2024.

---

## 🛠️ Estrutura de Arquivos e Pastas

### Scripts Python (`.py`)
* **`collect_bgp_data.py`**: Realiza requisições iniciais à API do RIPE Stat para buscar dados semanais brutos de anúncios BGP e status atual de roteamento dos ASNs.
* **`plot_bgp_data.py`**: Processa os arquivos JSON da coleta original e plota gráficos individuais de contagem de anúncios por operador BGP. Contém checagem de dados vazios de retiradas (*withdrawals*).
* **`cross_analyze_bgp_events.py`**: Primeiro script experimental de cruzamento sequencial de dados que correlaciona picos de instabilidade BGP com datas históricas dos conflitos.
* **`fast_cross_analysis.py`**: Script final otimizado. Utiliza concorrência paralela (`ThreadPoolExecutor`) para buscar dados em alta resolução diária (fatiamento de 14 dias), mescla séries temporais usando `pandas` e gera gráficos combinados com anotações cronológicas dos conflitos.

### Pastas Geradas
* **`/data`**: Armazena os dados brutos de histórico de roteamento e atividade de updates no formato JSON gerados pelos coletores.
* **`/graphs`**: Contém as visualizações finais em formato `.png`, incluindo os gráficos de cruzamento anotados com os eventos militares.

---

## 🔄 Fluxo de Trabalho (Workflow)

Para reproduzir os resultados e gerar as visualizações:

### 1. Pré-requisitos
Certifique-se de ter as bibliotecas necessárias instaladas:
```bash
pip install pandas matplotlib requests
```

### 2. Execução Recomendada (Pipeline de Cruzamento Histórico)
Para rodar a coleta diária assíncrona paralela e obter os gráficos combinados e anotados com a linha do tempo dos conflitos, execute:
```bash
python fast_cross_analysis.py
```
Isso atualizará os dados na pasta `/data` e criará os gráficos de análise cruzada `cross_analysis_2023.png` e `cross_analysis_2024.png` na pasta `/graphs`.

### 3. Execução Alternativa (Análise de Operadores Individuais)
Para executar a rotina de coleta e plotagem individual de gráficos por operador:
1. Colete os dados básicos:
   ```bash
   python collect_bgp_data.py
   ```
2. Gere as curvas individuais de atividade de updates:
   ```bash
   python plot_bgp_data.py
   ```
   Os gráficos serão salvos em `/graphs` sob o padrão de nome `chart_[periodo]_AS[numero].png`.

---

## 🎓 Contexto Acadêmico
Este projeto foi desenvolvido como parte do Trabalho de Redes no Mestrado em Informática da UFRJ.

### Declaração de Uso de IA Generativa
Este projeto utilizou a ferramenta de inteligência artificial generativa Gemini (Google) como apoio técnico durante o desenvolvimento, nas seguintes atividades:
* Apoio na documentação e organização do código-fonte
* Auxílio na depuração de erros de consulta à API e na otimização do script de coleta concorrente paralela.
* Suporte na formatação e ajustes estéticos dos gráficos de visualização de dados desenvolvidos em Matplotlib.

**Nota:** Toda a concepção da pesquisa, a definição da metodologia de cruzamento histórico, a modelagem dos scripts de coleta de dados BGP, a análise dos resultados e a correlação geopolítica dos apagões no Sudão foram realizadas pelos autores. A ferramenta de IA foi utilizada unicamente como apoio ao desenvolvimento e à documentação do software.
