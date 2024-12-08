import bs4
import time
import requests
import selenium


def login_prompt(confluence_login_link: str, webdriver: selenium.webdriver) -> bool | dict:
    """
    Prompt the user to login to Confluence.

    :param confluence_login_link: The Confluence login link.
    :param driver: The driver to use.
    :return: The cookies if the user successfully logs in. False otherwise.
    """

    print("Please login to Confluence.")

    try:
        webdriver.get(confluence_login_link)
    except Exception as e:
        print(f'Failed to load the Confluence login page: {e}')
        return False
    
    logging_in: bool = False
    login_title_list: list[str] = ['log in', 'login']
    duo_prompt: bool = False

    while True:
        current_page_name: str = webdriver.title

        if any(title in current_page_name.lower() for title in login_title_list):
            logging_in = True
        
        # Duo two-factor authentication
        if 'duo' in current_page_name.lower():
            if not duo_prompt:
                print('Please complete the two-factor authentication.')
                duo_prompt = True

            time.sleep(1)
            continue
        
        if logging_in and not any(title in current_page_name.lower() for title in login_title_list) and 'Atlassian' in current_page_name:
            break

        time.sleep(0.1)
    
    print('Successfully logged in to Confluence.')

    return webdriver.get_cookies()


def get_pages(session: requests.Session, query_url: str, query: dict) -> list[dict] | None:
    """
    Get the pages from Confluence.

    :param session: The session to use.
    :param query_url: The query URL.
    :param query: The query to use.
    :return: The pages from Confluence.
    """

    response: requests.Response = session.post(query_url, json=query, headers={'Content-Length': str(len(query)), 'Content-Type': 'application/json'})

    pages: list[dict] | None = response.json().get('data', {}).get('confluenceContentSearch', {}).get('nodes', None)

    return pages


def get_page_info(session: requests.Session, page_id: str, page_info_url: str, confluence_base_url: str, default_card_panel_name: str, card_info_skip: dict, verbose: bool) -> dict:
    """
    Get the information for a page.

    :param session: The session to use.
    :param page_id: The ID of the page.
    :param page_info_url: The URL to get the page information.
    :param confluence_base_url: The base URL of the Confluence site.
    :param default_card_panel_name: The default name for a card panel.
    :param card_info_skip: The information to skip.
    :param verbose: Whether to print verbose output.
    :return: The information for the page.
    """

    response: requests.Response = session.get(f'{page_info_url}{page_id}')

    data: dict = {}

    soup: bs4.BeautifulSoup = bs4.BeautifulSoup(response.text, 'html.parser')
    page_info_container = soup.find('div', {'class': 'page view-information'})
    info_cards = page_info_container.find_all('div', {'class': 'basicPanelContainer'})

    for card in info_cards:
        if card.find('div', {'class': 'basicPanelTitle'}) is None:
            card_title: str = default_card_panel_name
        else:
            card_title: str = card.find('div', {'class': 'basicPanelTitle'}).text
        card_title = card_title.strip()

        data[card_title] = {}
        
        card_body = card.find('div', {'class': 'basicPanelBody'})

        match card_title:
            case 'Labels':
                if card_info_skip.get('Labels', False):
                    continue

                label_types = card_body.find_all('div', {'class': 'label'})
                label_lists = card_body.find_all('ul', {'class': 'label-list'})

                if len(label_types) != len(label_lists) and verbose:
                    print('Mismatched label types and lists.')
                
                for i in range(0, len(label_types)):
                    label_type: str = label_types[i].text.strip().split(' (')[0]
                    data[card_title][label_type] = []

                    for label in label_lists[i].find_all('a'):
                        data[card_title][label_type].append(label.text)
                        
            case 'Recent Changes':
                continue
            case 'Incoming Links':
                if card_info_skip.get('Incoming Links', False):
                    continue

                links = card_body.find_all('a')

                for link in links:
                    if link['href'] is not None:
                        data[card_title][link.text] = link['href']

            case 'Outgoing Links':
                if card_info_skip.get('Outgoing Links', False):
                    continue

                links = card_body.find_all('a')

                for link in links:
                    if link['href'] is not None:
                        data[card_title][link.text] = link['href']

            case 'Hierarchy':
                continue

            case default_card_panel_name:
                if card_info_skip.get(default_card_panel_name, False) == True:
                    continue
                
                try:
                    table_container = card_body.find('table', {'class': 'pageInfoTable'})
                    info_items = table_container.find_all('tr')
                except:
                    print(card_body)

                for item in info_items:
                    key = item.find('th', {'class': 'label'})

                    if key is None:
                        continue

                    key = key.text.strip()

                    if key.endswith(':'):
                        key = key[:-1]

                    if key in card_info_skip.get('default_card_panel_name', []):
                        continue
                    
                    if key in ['Creator', 'Last Changed by']:
                        values = item.find_all('td')
                        value = {'user' : values[0].text.strip(), 'date' : values[1].text.strip()}
                    else:
                        value = item.find('td').text.strip()
                    
                    if key == 'Export As':
                        export_types: list = item.find_all('a')
                        value: dict = {}

                        for export_type in export_types:
                            export_link: str = export_type.get('href')

                            if export_link.startswith('/'):
                                export_link = f'{confluence_base_url}{export_link}'

                            value[export_type.text.strip()] = export_link

                    data[card_title][key] = value
    
    return data


def test_page_links(session: requests.Session, headers: dict, page: dict, base_url: str, link_ignore_types: list[str], ignore_links: list[str], timeout: int) -> dict:
    """
    Test the links on a page.

    :param session: The session to use.
    :param headers: The headers to use.
    :param page: The page to test.
    :param base_url: The base URL of the Confluence site.
    :param link_ignore_types: The types of links to ignore.
    :param timeout: The timeout for the request.
    :return: The links on the page.
    """

    links: dict = page.get('Outgoing Links', {})

    data: dict = {}

    for key, value in links.items():
        skip_link: bool = False

        for ignore_type in link_ignore_types:
            if value.startswith(ignore_type):
                skip_link: bool = True

        if skip_link:
            continue

        #Assume it's referencing itself
        if value.startswith('/'):
            value = f'{base_url}{value}'
        
        if value in ignore_links:
            continue

        try:
            response = session.get(value, timeout=timeout, headers=headers)
            data[value] = response.status_code
        except Exception as error:
            data[value] = error

            if value.startswith('http://') and not value.startswith('https://'):
                try:
                    response = session.get(value.replace('http://', 'https://', 1), timeout=timeout, headers=headers)
                    data[value] = response.status_code
                except requests.exceptions.RequestException:
                    data[value] = 'Error connecting'

    
    return data
