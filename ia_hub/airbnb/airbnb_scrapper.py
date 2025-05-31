import re
import os
import time
import logging
import subprocess
from datetime import datetime

import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Variável de ambiente para o ambiente de execução (local ou produção)
ENV = os.getenv("ENV", "local")


def _get_chrome_version():
    try:
        result = subprocess.run(
            ["google-chrome", "--version"], capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return "Chrome não encontrado"


def __setup_driver():
    """
    Configura e inicializa o driver do Chrome para Selenium.
    Adapta a configuração com base no ambiente (local ou produção).
    """
    try:
        logger.info("Configurando o driver do Chrome...")
        logger.info("Versão do Chrome instalada: %s", _get_chrome_version())

        options = Options()

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")  # Necessário em alguns ambientes Linux
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")  # Necessário em alguns ambientes Linux
        options.add_argument("--remote-debugging-port=9222")  # Porta para debug remoto

        if ENV != "local":
            options.add_argument("--headless=new")
            logger.info(
                "Executando em ambiente de produção. Usando Chrome em %s",
                options.binary_location,
            )

        service = Service(ChromeDriverManager(driver_version="137.0.0").install())
        driver = webdriver.Chrome(service=service, options=options)

        logger.info("Driver do Chrome configurado com sucesso.")
        return driver
    except WebDriverException as e:
        logger.error("❌ Erro ao configurar o driver do Chrome: %s", e)
        logger.error(
            "Verifique se o Chrome está instalado e se o ChromeDriver é compatível com sua versão do Chrome."
        )
        raise
    except Exception as e:
        logger.error("❌ Ocorreu um erro inesperado ao configurar o driver: %s", e)
        raise


def __extrair_titulo(driver):
    """
    Extrai o título do anúncio, tentando diferentes seletores.
    """
    logger.info("Extraindo título do anúncio...")
    titulo = "⚠️ Título não encontrado"

    # Tenta encontrar o título em um h1
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        h1_element = driver.find_element(By.TAG_NAME, "h1")
        titulo = h1_element.text.strip()
        if titulo:
            logger.info("Título encontrado (h1): %s", titulo)
            return titulo
    except TimeoutException:
        logger.warning("Timeout esperando pelo h1. Tentando seletores alternativos.")
    except NoSuchElementException:
        logger.warning("h1 não encontrado. Tentando seletores alternativos.")
    except Exception as e:
        logger.warning("Erro ao buscar h1: %s", e)

    # Tenta encontrar o título por data-testid
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="listing-page-title"]')
            )
        )
        titulo_alt = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="listing-page-title"]'
        ).text.strip()
        if titulo_alt:
            logger.info("Título alternativo encontrado (data-testid): %s", titulo_alt)
            return titulo_alt
    except TimeoutException:
        logger.warning("Timeout esperando por data-testid='listing-page-title'.")
    except NoSuchElementException:
        logger.warning("Elemento com data-testid='listing-page-title' não encontrado.")
    except Exception as e:
        logger.warning("Erro ao buscar título por data-testid: %s", e)

    logger.warning("Título não encontrado após todas as tentativas.")
    return titulo


def __extrair_preco_total(driver):
    """
    Extrai o preço total do anúncio, usando múltiplas estratégias e depuração.
    """
    logger.info("Iniciando extração do preço total...")
    preco_total = None
    textos_debug = []

    # Rola a página para garantir que elementos dinâmicos sejam carregados
    logger.info("Rolando a página para garantir que o preço seja renderizado...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)  # Pequeno delay para renderização após o scroll

    # Estratégia 1: Tentar encontrar o preço total por data-testid (comum no Airbnb)
    logger.info("Tentando encontrar preço por data-testid='book-it-total-price'...")
    try:
        # Espera por até 20 segundos pelo elemento do preço total
        preco_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="book-it-total-price"]')
            )
        )
        preco_total = preco_element.text.strip()
        if preco_total:
            logger.info("✅ Preço total encontrado por data-testid: %s", preco_total)
            return preco_total
    except TimeoutException:
        logger.warning("Timeout esperando por data-testid='book-it-total-price'.")
    except NoSuchElementException:
        logger.warning("Elemento com data-testid='book-it-total-price' não encontrado.")
    except Exception as e:
        logger.warning("Erro ao tentar encontrar preço por data-testid: %s", e)

    # Estratégia 2: Buscar por elementos com "R$" e palavras-chave como "Total", "noites", "diária"
    logger.info(
        "Tentando encontrar preço por XPATH genérico com 'R$' e palavras-chave..."
    )
    try:
        # Espera por até 15 segundos por qualquer elemento que contenha "R$"
        elementos_com_rs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//*[contains(text(),'R$')]")
            )
        )
        logger.debug("Encontrados %d elementos com 'R$'.", len(elementos_com_rs))

        for elem in elementos_com_rs:
            texto = elem.text.strip()
            textos_debug.append(texto)  # Adiciona para debug final
            logger.debug("Analisando elemento com texto: '%s'", texto)

            # Prioriza elementos que contenham "Total", "noite" ou "diária"
            if (
                "Total" in texto
                or "total" in texto
                or "noite" in texto
                or "diária" in texto
            ):
                # Verifica se o texto contém um valor numérico válido após "R$"
                if "R$" in texto:
                    # Regex para extrair o valor numérico (incluindo vírgula para decimal)

                    match = re.search(r"R\$\s*([\d\.,]+)", texto)
                    if match:
                        extracted_price = (
                            match.group(1).replace(".", "").replace(",", ".")
                        )  # Converte para formato numérico
                        try:
                            float(
                                extracted_price
                            )  # Tenta converter para float para validar
                            preco_total = texto
                            logger.info(
                                "✅ Preço total encontrado por XPATH com palavra-chave: %s",
                                preco_total,
                            )
                            return preco_total
                        except ValueError:
                            logger.debug(
                                "Texto '%s' contém R$ mas o valor não é numérico válido.",
                                texto,
                            )
                    else:
                        logger.debug(
                            "Texto '%s' contém R$ mas não foi possível extrair o valor numérico.",
                            texto,
                        )
            else:
                logger.debug(
                    "Texto '%s' não contém palavras-chave de preço total.", texto
                )

    except TimeoutException:
        logger.warning("Timeout esperando por elementos com 'R$'.")
    except NoSuchElementException:
        logger.warning("Nenhum elemento com 'R$' encontrado.")
    except Exception as e:
        logger.warning("Erro ao tentar encontrar preço por XPATH genérico: %s", e)

    # Estratégia 3: Buscar por aria-label ou outros data-atributos genéricos para preço/valor
    logger.info(
        "Tentando encontrar preço por aria-label ou data-atributos genéricos..."
    )
    try:
        # Busca por elementos com aria-label que contenham "preço" ou "valor"
        preco_aria = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[aria-label*="preço"], [aria-label*="valor"]')
            )
        )
        preco_total = preco_aria.text.strip()
        if preco_total:
            logger.info("✅ Preço alternativo encontrado (aria-label): %s", preco_total)
            return preco_total
    except TimeoutException:
        logger.warning("Timeout esperando por aria-label='preço'/'valor'.")
    except NoSuchElementException:
        logger.warning("Nenhum elemento com aria-label='preço'/'valor' encontrado.")
    except Exception as e:
        logger.warning("Erro ao tentar encontrar preço por aria-label: %s", e)

    # Estratégia 4: Tentar extrair preço via JavaScript (incluindo shadow DOM)
    logger.info("Tentando extrair preço via JavaScript (shadow DOM)...")
    try:
        js_code = """
        function getPriceFromShadowRoots() {
            let price = null;
            // Busca todos os elementos que podem conter shadow roots
            const allElems = document.querySelectorAll('*');
            for (const elem of allElems) {
                if (elem.shadowRoot) {
                    // Busca por qualquer texto com R$ dentro do shadow root
                    const matches = elem.shadowRoot.querySelectorAll('*');
                    for (const match of matches) {
                        if (match.innerText && match.innerText.includes('R$')) {
                            price = match.innerText;
                            if (price) return price;
                        }
                    }
                }
            }
            return price;
        }
        return getPriceFromShadowRoots();
        """
        preco_js = driver.execute_script(js_code)
        if preco_js:
            logger.info("✅ Preço encontrado via JavaScript/shadow DOM: %s", preco_js)
            return preco_js
    except Exception as e:
        logger.warning("Erro ao tentar extrair preço via JavaScript/shadow DOM: %s", e)

    logger.warning(
        "[DEBUG] Nenhum preço encontrado após todas as estratégias. Textos de elementos com 'R$' analisados: %s",
        textos_debug,
    )
    return None


def __verificar_disponibilidade(driver):
    """
    Verifica a disponibilidade do imóvel na página.
    """
    logger.info("Verificando disponibilidade do imóvel...")
    xpath_query = (
        "//*[contains(text(),'indisponível') or "
        "contains(text(),'Essas datas não estão disponíveis') or "
        "contains(text(),'não estão disponíveis') or "
        "contains(text(),'Não disponível')]"  # Adicionado mais uma variação
    )
    mensagem_indisponivel = None
    disponivel = True

    try:
        # Espera por um curto período para ver se alguma mensagem de indisponibilidade aparece
        indisponivel_elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, xpath_query))
        )
        if indisponivel_elements:
            mensagem_indisponivel = indisponivel_elements[0].text.strip()
            logger.info("❌ Imóvel indisponível: %s", mensagem_indisponivel)
            disponivel = False
        else:
            logger.info(
                "✅ Imóvel disponível nas datas selecionadas (nenhuma mensagem de indisponibilidade encontrada)."
            )
    except TimeoutException:
        logger.info(
            "✅ Nenhuma mensagem de indisponibilidade encontrada dentro do tempo limite."
        )
    except Exception as e:
        logger.warning("Erro ao verificar disponibilidade: %s", e)
        # Assume disponível se houver erro na verificação, mas loga o erro
        disponivel = True

    return disponivel, mensagem_indisponivel


def __scroll_until_price_or_timeout(driver, timeout=30):
    """
    Rola a página até encontrar um elemento de preço com "por x noites" ou até o timeout.
    """
    logger.info(
        "Rolando página até encontrar preço com 'por x noites' ou timeout de %d segundos...",
        timeout,
    )
    start_time = time.time()
    last_height = driver.execute_script("return document.body.scrollHeight")

    while time.time() - start_time < timeout:
        # Tenta encontrar o elemento antes de rolar para evitar scrolls desnecessários
        try:
            # Espera por um elemento que contenha "R$" e "noites" ou "diária"
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(text(),'R$') and (contains(text(),'noites') or contains(text(),'diária'))]",
                    )
                )
            )
            logger.info(
                "Elemento de preço com 'por x noites' ou 'diária' encontrado durante o scroll."
            )
            return True
        except TimeoutException:
            logger.debug("Elemento de preço não encontrado, continuando o scroll.")
        except Exception as e:
            logger.debug("Erro ao verificar elemento de preço durante o scroll: %s", e)

        # Rola a página para baixo
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Pequeno delay para carregar conteúdo após o scroll

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            logger.debug("Altura da página não mudou, fim do scroll.")
            break  # Não há mais para rolar

        last_height = new_height

    logger.warning("Timeout ao tentar encontrar preço rolando a página.")
    return False


def __get_rooms_ids(config):
    """
    Obtém os IDs dos quartos do banco de dados com base no owner_id da configuração.
    """
    logger.info("Obtendo ID do quarto a partir da configuração...")

    owner_id = None
    if config and isinstance(config, dict):
        metadata = config.get("metadata", {})
        owner_id = metadata.get("owner_id")

    if not owner_id:
        logger.error(
            "❌ owner_id não encontrado na configuração. Por favor, forneça um owner_id válido."
        )
        raise ValueError("owner_id não encontrado na configuração.")

    try:
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            logger.error("❌ Variável de ambiente POSTGRES_URL não definida.")
            raise ValueError("POSTGRES_URL não definida.")

        conn = psycopg2.connect(postgres_url)
        cur = conn.cursor()
        cur.execute("SELECT id FROM rooms WHERE owner_id = %s LIMIT 1", (owner_id,))
        result = cur.fetchall()
        cur.close()
        conn.close()

        ids = [row[0] for row in result]

        if ids:
            logger.info("Rooms ids encontrados para owner_id %s: %s", owner_id, ids)
            return ids
        else:
            logger.warning("Nenhum room id encontrado para owner_id %s.", owner_id)
            raise ValueError(f"Nenhum room id encontrado para owner_id {owner_id}.")
    except Exception as e:
        logger.error("❌ Erro ao buscar room id no banco de dados: %s", e)
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
    """
    Processa um único ID de quarto, acessando a URL do Airbnb e extraindo informações.
    """
    try:
        url = (
            f"https://www.airbnb.com.br/rooms/{room_id}?"
            f"check_in={check_in}&check_out={check_out}"
            f"&adults={adults}&guests={guests}"
        )

        logger.info("Acessando URL: %s", url)
        driver.get(url)

        # Tira screenshot inicial e salva o HTML para debug
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Espera pelo carregamento inicial da página (pode ser o título ou um elemento genérico)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.TAG_NAME, "body")
                )  # Espera pelo corpo da página
            )
            logger.info("Corpo da página carregado.")
        except TimeoutException:
            logger.error(
                "Timeout ao esperar pelo corpo da página. A página pode não ter carregado corretamente."
            )
            return "❌ Erro: Página não carregou completamente."

        # Rola a página até encontrar o preço ou atingir o timeout
        __scroll_until_price_or_timeout(driver)

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

        logger.info("Scraping finalizado para room_id %s.", room_id)

        return "\n".join(text_return)
    except Exception as e:
        logger.error(
            "❌ Ocorreu um erro ao extrair as informações para room_id %s: %s",
            room_id,
            e,
        )
        # Tenta tirar um screenshot final em caso de erro
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raise
    finally:
        # O driver será fechado na função initialize_airbnb_scraper
        pass


def initialize_airbnb_scraper(**kwargs):
    """
    Função principal para iniciar o processo de scraping do Airbnb.
    """
    logger.info("Iniciando scraping do Airbnb...")
    driver = None  # Inicializa driver como None
    try:
        check_in = kwargs.get("check_in")
        check_out = kwargs.get("check_out")
        guests = kwargs.get("guests", 1)
        adults = kwargs.get("adults", 1)
        config = kwargs.get("config", {})

        if not all([check_in, check_out]):
            logger.error("❌ check_in e check_out são parâmetros obrigatórios.")
            raise ValueError("check_in e check_out são obrigatórios.")

        driver = __setup_driver()  # Configura o driver

        rooms_ids = __get_rooms_ids(config)

        results = []
        for room_id in rooms_ids:
            logger.info("Processando room_id: %s", room_id)
            result = __process_each_room_id(
                driver, room_id, check_in, check_out, guests, adults
            )
            results.append(result)
            logger.info("Resultado do scraping para room_id %s: %s", room_id, result)

        return "\n\n".join(
            results
        )  # Retorna todos os resultados separados por duas quebras de linha

    except Exception as e:
        logger.error("❌ Ocorreu um erro ao iniciar o scraping: %s", e)
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("Driver do Chrome fechado.")
