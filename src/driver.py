from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

from selenium.webdriver.ie.service import Service as IEService
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import IEDriverManager, EdgeChromiumDriverManager

from selenium.webdriver.chrome import service
from webdriver_manager.opera import OperaDriverManager

from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.service import Service as ChromeService


def get_driver(browser: str) -> webdriver:
    """
    Get the driver for the specified browser.

    :param browser: The browser to use.
    :return: The driver for the specified browser.
    """

    options: webdriver.ChromeOptions = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_experimental_option('prefs', {"credentials_enable_service": False, "profile.password_manager_enabled": False})

    match browser:
        case 'Chrome':
            return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        case 'Chromium':
            return webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(), options=options)
        case 'Brave':
            return webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install(), options=options)
        case 'Firefox':
            return webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
        case 'Internet Explorer':
            return webdriver.Ie(service=IEService(IEDriverManager().install()))
        case 'Edge':
            return webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()))
        case 'Opera':
            webdriver_service = service.Service(OperaDriverManager().install())
            webdriver_service.start()

            return webdriver.Remote(webdriver_service.service_url, options=options)
        case _:
            raise ValueError(f'Unsupported browser: {browser}')


def load_wait(driver: webdriver, delay: int, by: type, type: str) -> bool:
    """
    Wait for an element to be present in the web page.

    :param by: The type of locator (e.g., By.XPATH, By.ID).
    :param type: The value of the locator (e.g., "//div[@class='example']").
    :return: True if the element is found within the specified timeout, False otherwise.
    """
    
    try:
        WebDriverWait(driver, delay).until(EC.presence_of_element_located((by, type)))
        return True
    except:
        print(f'unable to load element: {type}')
    
    return False