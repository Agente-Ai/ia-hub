import os
import time
import logging

import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "local")


def __setup_driver():
    try:
        logger.info("Configurando o driver do Chrome...")
        options = Options()

        if ENV == "local":
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            options.binary_location = "/usr/bin/google-chrome"
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--remote-debugging-port=9222")
            driver = webdriver.Chrome(options=options)

        logger.info("Chrome iniciado. Aguardando carregamento do body...")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return driver
    except Exception as e:
        logger.error("❌ Ocorreu um erro ao configurar o driver: %s", e)
        if hasattr(e, "msg"):
            logger.error("Mensagem do erro: %s", e.msg)
        if hasattr(e, "stacktrace"):
            logger.error("Stacktrace: %s", e.stacktrace)
        raise


def __extrair_titulo(driver):
    logger.info("Extraindo título do anúncio...")
    try:
        while True:
            titulo = driver.find_element(By.TAG_NAME, "h1").text.strip()
            if titulo != "Ajude-nos a melhorar sua experiência":
                logger.info("Título encontrado: %s", titulo)
                return titulo
            logger.info("Página ainda não carregou o título correto. Aguardando...")
            time.sleep(1)
    except Exception as e:
        logger.warning("Título não encontrado: %s", e)
        return "⚠️ Título não encontrado"


def __extrair_preco_total(driver):
    logger.info("Extraindo preço total...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'R$')]"))
        )
    except Exception as e:
        logger.warning("Elemento com 'R$' não encontrado imediatamente: %s", e)
        raise

    elementos = driver.find_elements(By.XPATH, "//*[contains(text(),'R$')]")
    preco_total = None
    textos_debug = []

    for elem in elementos:
        texto = elem.text.strip()
        textos_debug.append(texto)
        if "noite" in texto and "R$" in texto:
            preco_total = texto
            logger.info("Preço total encontrado (com noite): %s", preco_total)
            break

    if not preco_total:
        for texto in textos_debug:
            if "R$" in texto and "noite" not in texto:
                preco_total = texto
                logger.info("Preço total encontrado (sem noite): %s", preco_total)
                break

    if not preco_total:
        logger.warning("[DEBUG] Nenhum preço encontrado. Textos: %s", textos_debug)

    return preco_total


def __verificar_disponibilidade(driver):
    logger.info("Verificando disponibilidade do imóvel...")
    xpath_query = (
        "//*[contains(text(),'indisponível') or "
        "contains(text(),'Essas datas não estão disponíveis') or "
        "contains(text(),'não estão disponíveis')]"
    )
    indisponivel = driver.find_elements(By.XPATH, xpath_query)
    mensagem_indisponivel = None
    if indisponivel:
        mensagem_indisponivel = indisponivel[0].text.strip()
        logger.info("Imóvel indisponível: %s", mensagem_indisponivel)
    else:
        logger.info("Imóvel disponível nas datas selecionadas.")
    return len(indisponivel) == 0, mensagem_indisponivel


def __scroll_until_price(driver, timeout=20):
    logger.info("Rolando página até encontrar preço com 'por x noites' ou timeout...")
    start_time = time.time()
    last_height = driver.execute_script("return document.body.scrollHeight")
    while time.time() - start_time < timeout:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        logger.debug("Scroll realizado até o final da página.")
        time.sleep(2)
        elementos = driver.find_elements(
            By.XPATH, "//*[contains(text(),'por') and contains(text(),'noite')]"
        )
        if elementos:
            logger.info("Elemento de preço com 'por x noites' encontrado.")
            return True
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            logger.debug("Altura da página não mudou, fim do scroll.")
            break
        last_height = new_height
    logger.warning("Timeout ao tentar encontrar preço rolando a página.")
    return False


def __get_rooms_ids(config):
    logger.info("Obtendo ID do quarto a partir da configuração...")

    owner_id = None
    if config and isinstance(config, dict):
        metadata = config.get("metadata", {})
        owner_id = metadata.get("owner_id")

    if not owner_id:
        logger.warning("owner_id não encontrado na configuração. Usando valor padrão.")
        raise ValueError("owner_id não encontrado na configuração.")

    try:
        conn = psycopg2.connect(os.getenv("POSTGRES_URL", ""))
        cur = conn.cursor()
        cur.execute("SELECT id FROM rooms WHERE owner_id = %s LIMIT 1", (owner_id,))
        result = cur.fetchall()
        cur.close()
        conn.close()

        # Extrai apenas os ids do resultado (que vem como lista de tuplas)
        ids = [row[0] for row in result]

        if ids:
            logger.info("Rooms ids encontrados para owner_id %s: %s", owner_id, ids)
            return ids
        else:
            logger.warning(
                "Nenhum room id encontrado para owner_id %s. Usando padrão.", owner_id
            )
            raise ValueError(f"Nenhum room id encontrado para owner_id {owner_id}.")
    except Exception as e:
        logger.error("Erro ao buscar room id no banco: %s", e)
        raise ValueError(
            f"Erro ao buscar room id no banco para owner_id {owner_id}: {e}"
        ) from e


def __process_each_room_id(
    driver,
    room_id,
    check_in,
    check_out,
    guests,
    adults,
):
    try:
        url = (
            f"https://www.airbnb.com.br/rooms/{room_id}?"
            f"check_in={check_in}&check_out={check_out}"
            f"&adults={adults}&guests={guests}"
        )

        logger.info("Acessando URL: %s", url)
        driver.get(url)

        __scroll_until_price(driver)

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
            if mensagem_indisponivel:
                text_return.append(f"📝 Motivo: {mensagem_indisponivel}")

        logger.info("Scraping finalizado.")

        return "\n".join(text_return)
    except Exception as e:
        logger.error("❌ Ocorreu um erro ao extrair as informações: %s", e)
        raise
    finally:
        driver.quit()
        logger.info("Driver fechado.")


def initialize_airbnb_scraper(**kwargs):
    logger.info("Iniciando scraping do Airbnb...")
    driver = __setup_driver()
    try:
        check_in = kwargs.get("check_in")
        check_out = kwargs.get("check_out")
        guests = kwargs.get("guests", 1)
        adults = kwargs.get("adults", 1)
        config = kwargs.get("config", {})

        rooms_ids = __get_rooms_ids(config)

        for room_id in rooms_ids:
            logger.info("Processando room_id: %s", room_id)
            result = __process_each_room_id(
                driver, room_id, check_in, check_out, guests, adults
            )
            logger.info("Resultado do scraping: %s", result)
            return result

    except Exception as e:
        logger.error("❌ Ocorreu um erro ao iniciar o scraping: %s", e)
        raise
