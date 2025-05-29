import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


def __setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    return driver


def __extrair_titulo(driver):
    try:
        titulo = driver.find_element(By.TAG_NAME, "h1").text.strip()
        return titulo
    except Exception:
        return "⚠️ Título não encontrado"


def __extrair_preco_total(driver):
    # Busca spans com "R$"
    spans = driver.find_elements(By.XPATH, "//span[contains(text(),'R$')]")
    preco_total = None

    # Procura o preço com informação de noites (mais completo)
    for span in spans:
        texto = span.text.strip()
        if "noite" in texto and "R$" in texto:
            preco_total = texto
            break

    # Se não encontrou preço com noites, procura outros valores
    if not preco_total:
        # No Airbnb atual, o total geralmente não tem a palavra "Total"
        for span in spans:
            texto = span.text.strip()
            if "R$" in texto and "noite" not in texto:
                preco_total = texto
                break

    return preco_total


def __verificar_disponibilidade(driver):
    # Verifica diferentes mensagens de indisponibilidade que podem aparecer
    xpath_query = (
        "//*[contains(text(),'indisponível') or "
        "contains(text(),'Essas datas não estão disponíveis') or "
        "contains(text(),'não estão disponíveis')]"
    )

    indisponivel = driver.find_elements(By.XPATH, xpath_query)

    # Salvar a mensagem encontrada para debug e exibição
    mensagem_indisponivel = None
    if indisponivel:
        mensagem_indisponivel = indisponivel[0].text.strip()

    # Se não encontrou nenhuma das mensagens, está disponível
    return len(indisponivel) == 0, mensagem_indisponivel


def initialize_airbnb_scraper(**kwargs):
    try:
        driver = __setup_driver()

        config = kwargs.get("config", {})
        check_in = kwargs.get("check_in")
        check_out = kwargs.get("check_out")
        guests = kwargs.get("guests", 1)
        adults = kwargs.get("adults", 1)
        metadata = config.get("metadata", {})
        thread_id = metadata.get("thread_id")

        print("Checking availability for:")
        print(f"  Check-in: {check_in}")
        print(f"  Check-out: {check_out}")
        print(f"  Guests: {guests}")
        print(f"  Adults: {adults}")
        print(f"  Thread ID: {thread_id}")
        print(f"  Config: {config}")

        # TODO: Obter o room_id dinamicamente, se possível
        # Através do thread_id ou de outra forma

        room_id = "769729843373520689"

        # URL com os parâmetros fornecidos via linha de comando
        url = (
            f"https://www.airbnb.com.br/rooms/{room_id}?"
            f"check_in={kwargs['check_in']}&check_out={kwargs['check_out']}"
            f"&adults={kwargs['adults']}"
        )
        print(f"🔗 URL: {url}")

        driver.get(url)
        time.sleep(5)  # Wait for the page to load

        # Obtém as informações
        titulo = __extrair_titulo(driver)
        preco_total = __extrair_preco_total(driver)
        disponivel, mensagem_indisponivel = __verificar_disponibilidade(driver)

        text_return = [f"🏡 Título do anúncio: {titulo}"]

        if preco_total:
            text_return.append(f"💰 Valor total: {preco_total}")
        else:
            text_return.append("⚠️ Preço não encontrado.")

        if disponivel:
            text_return.append("✅ Imóvel disponível nas datas selecionadas.")
        else:
            text_return.append("❌ Imóvel indisponível nas datas selecionadas.")
            # Se tiver uma mensagem específica, mostre-a
            if mensagem_indisponivel:
                text_return.append(f"📝 Motivo: {mensagem_indisponivel}")

        return "\n".join(text_return)
    except Exception as e:
        print(f"❌ Ocorreu um erro ao extrair as informações: {e}")
    finally:
        # Fecha o navegador
        driver.quit()
