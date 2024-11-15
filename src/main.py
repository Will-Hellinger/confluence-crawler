import os
import time
import requests
import argparse
import selenium
import threading

import driver
import data_manager
import confluence_manager


thread_info: dict = {}


def scrape_thread(thread_number: int, session: requests.Session, headers: dict, pages: dict, confluence_info: dict, default_card_panel_name: str, card_info_skip: dict, link_ignore_types: list[str], timeout: int, verbose: bool) -> None:
    """
    Thread function to scrape the pages.

    :param thread_number: The thread number.
    :param session: The session to use.
    :param headers: The headers to use.
    :param pages: The pages to scrape.
    :param confluence_info: The Confluence info.
    :param default_card_panel_name: The default card panel name.
    :param card_info_skip: The card info to skip.
    :param link_ignore_types: The types of links to ignore.
    :param timeout: The timeout to use.
    :param verbose: Enable verbose mode.
    :return: None
    """

    global thread_info

    confluence_base_url: str = confluence_info.get('base_url', '')
    confluence_page_info_url: str = f'{confluence_base_url}{confluence_info.get('page_info_url', '')}'

    info: dict = {"current_page": "", "page_count_given": len(pages.keys()), "page_count": 0, "link_count" : 0, "failed_links": {}}

    for key, value in pages.items():
        page: dict = confluence_manager.get_page_info(session, key, confluence_page_info_url, default_card_panel_name, card_info_skip, verbose)

        info['current_page'] = value
        info['page_count'] += 1

        page_links: dict = confluence_manager.test_page_links(session, headers, page, confluence_base_url, link_ignore_types, timeout)

        for link, status in page_links.items():
            info['link_count'] += 1

            if status not in (200, 401):
                info['failed_links'][link] = page.get(default_card_panel_name, {}).get('Title', 'Unknown')
        
        thread_info[thread_number] = info
    
    session = requests.Session() # Clear the session


def info_thread(verbose: bool) -> None:
    """
    Thread function to print the info.

    :param verbose: Enable verbose mode.
    :return: None
    """

    global thread_info

    while True:
        status_lines = []

        if thread_info == {}:
            if verbose:
                print('Waiting for threads to start...')

            time.sleep(0.5)
            continue

        threads_alive: bool = False

        for thread_number, info in thread_info.items():
            status_lines.append(f'T{thread_number}: {info["page_count"]}/{info["page_count_given"]} : {info["page_count"]/info["page_count_given"] * 100:.2f}%')

            if not (info['page_count'] >= info['page_count_given']):
                threads_alive = True
        
        if not threads_alive:
            if verbose:
                print('Threads finished.')

            break
        
        if verbose:
            print(' | '.join(status_lines), end='\r')

        time.sleep(0.5)


def main(data: dict, query_data: dict, headers:dict, page_count: int, thread_count: int, verbose: bool) -> None:
    """
    Main function to check the links in Confluence.

    :param data: The data to use.
    :param query_data: The query data to use.
    :param headers: The headers to use.
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

    scan_session: requests.Session = requests.Session() # Create a session to use the cookies

    for cookie in cookies:
        scan_session.cookies.set(cookie['name'], cookie['value'])
    
    pages_raw: list[dict] = confluence_manager.get_pages(scan_session, confluence_query_url, query_data)
    pages: dict = {page['id']: page['title'] for page in pages_raw}

    link_count: int = 0
    failed_link_count: int = 0

    if verbose:
        print(f'Found {len(pages.keys())} pages!')

    page_chunks: list[dict] = [{} for _ in range(thread_count)]
    for idx, (page_id, page_title) in enumerate(pages.items()):
        page_chunks[idx % thread_count][page_id] = page_title

    threads: list[threading.Thread] = []

    scraping_start_time: float = time.time()

    for i in range(0, thread_count):
        session = requests.Session()
        session.cookies.update(scan_session.cookies)

        if verbose:
            print(f'Starting thread {i}...')

        thread = threading.Thread(target=scrape_thread, args=(i, session, headers, page_chunks[i], confluence_info, default_card_panel_name, card_info_skip, link_ignore_types, timeout, verbose))
        threads.append(thread)
        thread.start()
    
    info_thread_thread = threading.Thread(target=info_thread, args=(verbose,))
    info_thread_thread.start()
    
    for thread in threads:
        thread.join()
    
    info_thread_thread.join()

    for thread_number, info in thread_info.items():
        link_count += info['link_count']
        failed_link_count += len(info['failed_links'])

        if verbose:
            for link, page in info['failed_links'].items():
                print(f'Failed link: {link} : {page}')

    if verbose:
        print(f'Checking took {time.time() - scraping_start_time:.2f} seconds.')

    if link_count == 0:
        print('No links found.')
    elif failed_link_count == 0:
        print(f'All {link_count} links are working!')
    else:
        print(f'Failed links: {failed_link_count}/{link_count} : {failed_link_count/link_count * 100:.2f}%')
            

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Confluence Dead Link Checker')

    parser.add_argument('-d', '--data', type=str, help='The path to the JSON data file.')
    parser.add_argument('-q', '--query', type=str, help='The path to a queryJSON file.')
    parser.add_argument('-head', '--headers', type=str, help='The path to the headers file.')
    parser.add_argument('-c', '--count', type=int, help='The max number of pages to check.', default=1000)
    parser.add_argument('-t', '--threads', type=int, help='The number of threads to use.', default=1)
    parser.add_argument('-s', '--spaces', type=str, help='The spaces to check. (e.g., "space1,space2")')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode.')

    args: argparse.Namespace = parser.parse_args()

    default_data_path: str = f'.{os.sep}data{os.sep}default_info.json'
    data_path: str = f'.{os.sep}data{os.sep}info.json'
    header_path: str = f'.{os.sep}data{os.sep}headers.json'

    if args.data:
        data_path = args.data
    
    if args.headers:
        header_path = args.headers

    query_path: str = f'.{os.sep}data{os.sep}pages_query.json'

    if args.query:
        query_path = args.query
    
    if os.path.exists(data_path) and os.path.exists(query_path):
        data: dict = data_manager.load_json(data_path)
        query: dict = data_manager.load_json(query_path)
    else:
        print('Failed to load the JSON files.')
        exit(1)
    
    if os.path.exists(header_path):
        headers: dict = data_manager.load_json(header_path)
    else:
        headers = {}
        print('Failed to load the headers file.')

    if not args.spaces and data.get('confluence_info').get('spaces') is None:
        print('Please specify the spaces to check.')
        exit(1)

    if args.spaces:
        spaces = args.spaces.split(',')
        data['confluence_info']['spaces'] = spaces

    main(data, query, headers, args.count, args.threads, args.verbose)