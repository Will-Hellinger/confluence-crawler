import os
import time
import shutil
import requests
import argparse
import selenium

import driver
import data_manager
import confluence_manager


def main(data: dict, query_data: dict, page_count: int, verbose: bool) -> None:
    """
    Main function to check the links in Confluence.

    :param data: The data to use.
    :param query_data: The query data to use.
    :param page_count: The max number of pages to check.
    :param verbose: Enable verbose mode.
    :return: None
    """

    start_time: float = time.time()

    confluence_info: dict = data.get('confluence_info', {})
    confluence_base_url: str = confluence_info.get('base_url', '')
    confluence_query_url: str = f'{confluence_base_url}{confluence_info.get('query_url', '')}'
    confluence_page_info_url: str = f'{confluence_base_url}{confluence_info.get('page_info_url', '')}'
    spaces: list[str] = confluence_info.get('spaces', [])

    if None in confluence_info.values():
        print('Please fill in the Confluence info in the data file.')
        exit(1)

    query_data['variables']['filters']['spaces']['spaceKeys'] = spaces # Update the spaces to check
    query_data['variables']['first'] = page_count
    query_data['variables']['maxNumberOfResults'] = page_count

    timeout: int = data.get('timeout', 3)

    default_card_panel_name: str = data.get('default_card_panel_name', 'Basic Info')
    link_ignore_types: list[str] = data.get('link_ignore_types', [])
    card_info_skip: dict = data.get('info_skip', {})

    # Open the browser and login to Confluence to get the cookies
    if verbose:
        browser_start_time: float = time.time()
        print(f'Setup took {time.time() - start_time:.2f} seconds.')
        print('Opening the browser...')

    webdriver: selenium.webdriver = driver.get_driver(data.get('browser', 'Chrome').title())
    cookies: bool | dict = confluence_manager.login_prompt(confluence_info.get('base_url', ''), webdriver)
    webdriver.quit()

    if cookies is False:
        print('Failed to login to Confluence.')
        exit(1)
    
    if verbose:
        print(f'Browser setup took {time.time() - browser_start_time:.2f} seconds.')
        print('Checking pages...')

    session: requests.Session = requests.Session() # Create a session to use the cookies

    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    
    pages_raw: list[dict] = confluence_manager.get_pages(session, confluence_query_url, query_data)
    pages: dict = {page['id']: page['title'] for page in pages_raw}

    total_pages = len(pages.keys())

    link_count: int = 0
    failed_link_count: int = 0
    failed_links: dict = {}
    
    current_page: int = 1

    if verbose:
        print(f'Found {len(pages.keys())} pages!')
    
    longest_link_length: int = max(len(link) for link in pages.values())

    for key, value in pages.items():
        if verbose:
            print(f'Checking page: {value} | {current_page}/{total_pages}{" " * (longest_link_length - len(value))}', end='\r')

        page: dict = confluence_manager.get_page_info(session, key, confluence_page_info_url, default_card_panel_name, card_info_skip, verbose)

        page_links: dict = confluence_manager.test_page_links(session, page, confluence_base_url, link_ignore_types, timeout)

        current_page += 1

        for link, status in page_links.items():
            link_count += 1

            if status not in (200, 401):
                failed_links[link] = value
                failed_link_count += 1
    
    for link, page in failed_links.items():
        print(f'Failed link: {link} | Page: {page}')

    print(f'Failed links: {failed_link_count}/{link_count} : {failed_link_count/link_count * 100:.2f}%')
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Confluence Dead Link Checker')

    parser.add_argument('-d', '--data', type=str, help='The path to the JSON data file.')
    parser.add_argument('-q', '--query', type=str, help='The path to a queryJSON file.')
    parser.add_argument('-c', '--count', type=int, help='The max number of pages to check.', default=1000)
    parser.add_argument('-s', '--spaces', type=str, help='The spaces to check. (e.g., "space1,space2")')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode.')

    args: argparse.Namespace = parser.parse_args()

    default_data_path: str = f'.{os.sep}data{os.sep}default_info.json'
    data_path: str = f'.{os.sep}data{os.sep}info.json'
    if args.data:
        data_path = args.data

    query_path: str = f'.{os.sep}data{os.sep}pages_query.json'
    if args.query:
        query_path = args.query

    if not os.path.exists(data_path) and os.path.exists(default_data_path):
        shutil.copyfile(default_data_path, data_path)
    else:
        print('Failed to find the default data file.')
        exit(1)
    
    if os.path.exists(data_path) and os.path.exists(query_path):
        data: dict = data_manager.load_json(data_path)
        query: dict = data_manager.load_json(query_path)
    else:
        print('Failed to load the JSON files.')
        exit(1)

    if not args.spaces and data.get('confluence_info').get('spaces') is None:
        print('Please specify the spaces to check.')
        exit(1)

    if args.spaces:
        spaces = args.spaces.split(',')
        data['confluence_info']['spaces'] = spaces

    main(data, query, args.count, args.verbose)