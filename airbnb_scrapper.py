import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC


def __setup_driver():
    options = Options()

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    return driver


def __extrair_titulo(driver):
    try:
        titulo = driver.find_element(By.TAG_NAME, "h1").text.strip()
        return titulo
    except Exception:
        return "⚠️ Título não encontrado"


def __extrair_preco_total(driver):
    # Tenta esperar explicitamente por qualquer elemento com 'R$' no texto
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'R$')]"))
        )
    except Exception:
        pass  # Continua mesmo se não encontrar explicitamente

    # Busca spans, divs, buttons, strong, etc. com 'R$'
    elementos = driver.find_elements(By.XPATH, "//*[contains(text(),'R$')]")
    preco_total = None
    textos_debug = []

    # Procura o preço com informação de noites (mais completo)
    for elem in elementos:
        texto = elem.text.strip()
        textos_debug.append(texto)
        if "noite" in texto and "R$" in texto:
            preco_total = texto
            break

    # Se não encontrou preço com noites, procura outros valores
    if not preco_total:
        for texto in textos_debug:
            if "R$" in texto and "noite" not in texto:
                preco_total = texto
                break

    # Debug: imprime todos os textos encontrados com 'R$'
    if not preco_total:
        print("[DEBUG] Nenhum preço encontrado. Textos:")
        for t in textos_debug:
            print(t)

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


def __scroll_until_price(driver, timeout=10):
    """Rola a página até encontrar um texto com 'R$' ou até atingir o timeout"""
    start_time = time.time()
    last_height = driver.execute_script("return document.body.scrollHeight")

    while time.time() - start_time < timeout:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # dá tempo pro JS carregar conteúdo

        # Verifica se apareceu algum elemento com 'R$'
        elementos = driver.find_elements(By.XPATH, "//*[contains(text(),'R$')]")
        if elementos:
            return True

        # Verifica se chegou ao fim da página (sem crescimento)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    return False


def initialize_airbnb_scraper(**kwargs):
    driver = __setup_driver()

    try:
        check_in = kwargs.get("check_in")
        check_out = kwargs.get("check_out")
        guests = kwargs.get("guests", 1)
        adults = kwargs.get("adults", 1)

        # config = kwargs.get("config", {})
        # metadata = config.get("metadata", {})
        # thread_id = metadata.get("thread_id")

        # TODO: Obter o room_id dinamicamente, se possível
        # Através do thread_id ou de outra forma

        room_id = "769729843373520689"

        # URL com os parâmetros fornecidos via linha de comando
        url = (
            f"https://www.airbnb.com.br/rooms/{room_id}?"
            f"check_in={check_in}&check_out={check_out}"
            f"&adults={adults}&guests={guests}"
        )
        driver.get(url)

        __scroll_until_price(driver)

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
