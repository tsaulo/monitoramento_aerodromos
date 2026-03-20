import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime


# Configurações

SITES_DIR = "sites"
HISTORICO_FILE = "historico.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Monitor Aerodromos)"
}


# Utilidades JSON

def carregar_json(arquivo):
    if not os.path.exists(arquivo):
        return {}
    with open(arquivo, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)



# Carregar sites

def carregar_sites():
    sites = []

    if not os.path.exists(SITES_DIR):
        print("Pasta 'sites' não encontrada.")
        return sites

    for arquivo in os.listdir(SITES_DIR):
        if arquivo.endswith(".json"):
            caminho = os.path.join(SITES_DIR, arquivo)
            dados = carregar_json(caminho)
            if dados:
                sites.append(dados)

    return sites


# Download página

def baixar_pagina(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


# Contar palavras

def contar_palavras(texto, palavras):
    texto = texto.lower()
    total = 0
    for p in palavras:
        total += texto.count(p.lower())
    return total


# Extrair links

def extrair_links(soup, selector, filtro_texto=None):
    container = soup.select_one(selector)

    if not container:
        return []

    links = []

    for a in container.find_all("a", href=True):
        texto = a.get_text(" ", strip=True)
        href = a["href"]

        if filtro_texto:
            texto_lower = texto.lower()

            # se for lista
            if isinstance(filtro_texto, list):
                if not any(f.lower() in texto_lower for f in filtro_texto):
                    continue

            # se for string
            else:
                if filtro_texto.lower() not in texto_lower:
                    continue

        links.append({
            "texto": texto,
            "url": href
        })

    return links


# Processar aeródromo

def processar_aerodromo(soup, aero):

    resultado = {}

    for tipo, dados in aero["monitorar"].items():

        # CASO: MONITORAR LINKS

        if dados.get("tipo") == "links":

            links = extrair_links(
                soup,
                dados["container_selector"],
                dados.get("filtro_texto")
            )

            resultado[tipo] = len(links)

        # CASO: MONITORAR PALAVRAS
        else:
            texto = ""

            if "div_id" in aero:
                div = soup.find("div", id=aero["div_id"])
                if div:
                    texto = div.get_text(" ", strip=True)

            elif "section_id" in dados:
                section = soup.find("section", id=dados["section_id"])
                if section:
                    texto = section.get_text(" ", strip=True)

            if not texto:
                continue

            qtd = contar_palavras(
                texto,
                dados["palavras_chave"]
            )

            resultado[tipo] = qtd

    return resultado

# Monitor principal

def monitorar():

    sites = carregar_sites()
    historico = carregar_json(HISTORICO_FILE)

    novos_dados = {}
    atualizados = []
    relatorio = []

    print("Monitoramento iniciado\n")

    for site in sites:

        site_resultado = {
            "nome": site["nome"],
            "aerodromos": []
        }

        try:
            html = baixar_pagina(site["url"])
        except Exception as e:
            print("ERRO:", e)
            continue

        soup = BeautifulSoup(html, "html.parser")

        for aero in site["aerodromos"]:

            codigo = aero["codigo"]
            nome_aerodromo = aero["nome_aerodromo"]

            aero_resultado = {
                "codigo": codigo,
                "nome": nome_aerodromo,
                "secoes": []
            }

            resultado = processar_aerodromo(soup, aero)

            if not resultado:
                continue

            antigo = historico.get(codigo, {})
            novos_dados[codigo] = {}

            for tipo, valor in resultado.items():

                antes = antigo.get(tipo, 0)

                if valor > antes:
                    atualizados.append({
                        "site": site["nome"],
                        "codigo": codigo,
                        "nome": nome_aerodromo,
                        "secao": tipo,
                        "novos": valor - antes
                    })
                    status = f"Atualizado (+{valor - antes})"
                else:
                    status = "Sem mudança"

                aero_resultado["secoes"].append({
                    "nome": tipo,
                    "status": status
                })

                novos_dados[codigo][tipo] = valor

        relatorio.append(site_resultado)

    # RESUMO

    print("\n------ RESUMO ------\n")

    if not atualizados:
        print("Nenhuma atualização encontrada.")
    else:
        print("!!! Atualizações detectadas:\n")

        for item in atualizados:
            print(f"{item['nome']} ({item['codigo']})")
            print(f"   Site: {item['site']}")
            print(f"   Seção: {item['secao']}")

            if "novo_link" in item:
                print(f"   Novo arquivo: {item['novo_link']}")
            else:
                print(f"   Novos: +{item['novos']}")

            print()

    # Relatório completo

    opcao = input("Deseja ver o relatório completo? (s/n): ").strip().lower()

    if opcao == "s":
        print("\n RELATÓRIO COMPLETO\n")

        for site in relatorio:
            print(f"------ {site['nome']} ------\n")

            for aero in site["aerodromos"]:
                print(f"{aero['nome']} ({aero['codigo']})")
                for secao in aero["secoes"]:
                    print(f"   - {secao['nome']}: {secao['status']}")
                print()

    salvar_json(HISTORICO_FILE, novos_dados)

    print("\nHistórico salvo")
    print(datetime.now().strftime("%d/%m/%Y %H:%M"))


# Começar

if __name__ == "__main__":
    monitorar()
