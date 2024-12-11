import os
import time
import json
import shutil
import getpass
import requests
import argparse
import selenium
import threading

import driver
import data_manager
import confluence_manager


def scrape_thread(thread_number: int, session: requests.Session, headers: dict, pages: dict, confluence_info: dict, default_card_panel_name: str, card_info_skip: dict, link_ignore_types: list[str], ignore_links: list[str], timeout: int, export: bool, export_path: str, verbose: bool) -> None:
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
    :param ignore_links: The links to ignore.
    :param timeout: The timeout to use.
    :param export: Export the pages to word documents.
    :param export_path: The path to export the word documents.
    :param verbose: Enable verbose mode.
    :return: None
    """

    global thread_info

    confluence_base_url: str = confluence_info.get('base_url', '')
    confluence_page_info_url: str = f'{confluence_base_url}{confluence_info.get('page_info_url', '')}'

    info: dict = {"current_page": "", "page_count_given": len(pages.keys()), "page_count": 0, "link_count" : 0, "failed_links": {}}

    for key, value in pages.items():
        page: dict = confluence_manager.get_page_info(session, key, confluence_page_info_url, confluence_base_url, default_card_panel_name, card_info_skip, verbose)

        info['current_page'] = value
        info['page_count'] += 1

        page_links: dict = confluence_manager.test_page_links(session, headers, page, confluence_base_url, link_ignore_types, ignore_links, timeout)

        if export:
            page_download_link: str = page.get(default_card_panel_name, {}).get('Export As', {}).get('Word', None)

            if page_download_link is not None:
                page_data: requests.Response = session.get(page_download_link)

                if page_data.status_code == 200:
                    with open(f'{export_path}{value.replace(os.sep, '_')}.doc', 'wb') as file:
                        file.write(page_data.content)

        for link, status in page_links.items():
            info['link_count'] += 1

            if status not in (200, 401):
                info['failed_links'][link] = value
        
        thread_info[thread_number] = info
    
    session = None # Clear the session


def info_thread() -> None:
    """
    Thread function to print the info.

    :return: None
    """

    global thread_info

    while True:
        status_lines: list[str] = []

        if thread_info == {}:
            print('Waiting for threads to start...')

            time.sleep(0.5)
            continue

        threads_alive: bool = False

        for thread_number, info in thread_info.items():
            status_lines.append(f'T{thread_number}: {info["page_count"]/info["page_count_given"] * 100:.2f}%')

            if not (info['page_count'] >= info['page_count_given']):
                threads_alive = True
        
        if not threads_alive:
            print('Threads finished.')

            break
        
        print(' | '.join(status_lines), end='\r')

        time.sleep(0.5)


def generate_log(thread_info: dict, logs_path: str, verbose: bool) -> None:
    """
    Generate the log.

    :param thread_info: The thread info.
    :param logs_path: The path to the logs.
    :param verbose: Enable verbose mode.
    :return: None
    """

    date: str = time.strftime('%Y-%m-%d_%H-%M-%S')

    if verbose:
        print(f'Generating log at {logs_path}log_{date}.txt...')

    with open(f'{logs_path}log_{date}.txt', 'w') as file:
        for thread_number, info in thread_info.items():
            file.write(f'Thread {thread_number}:\n')

            for link, page in info['failed_links'].items():
                file.write(f'{link} : {page}\n')

            file.write('\n')


def main(data: dict, query_data: dict, headers:dict, page_count: int, thread_count: int, export: bool, export_path: str, log: bool, logs_path: str, cookie_cache: bool | dict, cookie_path: str, master_key: bytes | None, verbose: bool) -> None:
    """
    Main function to check the links in Confluence.

    :param data: The data to use.
    :param query_data: The query data to use.
    :param headers: The headers to use.
    :param page_count: The max number of pages to check.
    :param thread_count: The number of threads to use.
    :param export: Export the pages to word documents.
    :param export_path: The path to export the word documents.
    :param logs_path: The path to the logs.
    :param cookie_cache: The cookie cache.
    :param cookie_path: The path to the cookie cache.
    :param master_key: The master key to use.
    :param verbose: Enable verbose mode.
    :return: None
    """

    global thread_info

    start_time: float = time.time()

    confluence_info: dict = data.get('confluence_info', {})
    confluence_base_url: str = confluence_info.get('base_url', '')
    confluence_query_url: str = f'{confluence_base_url}{confluence_info.get('query_url', '')}'
    
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
    ignore_links: list[str] = data.get('ignore_links', [])
    card_info_skip: dict = data.get('info_skip', {})

    if cookie_cache is not False:
        if len(cookie_cache) == 0:
            cookie_cache = False
        else:
            for cookie in cookie_cache:
                cookie_expirey: int | None = cookie.get('expiry', None)

                if cookie_expirey is None:
                    continue

                if cookie_expirey <= time.time():
                    cookie_cache = False
                    break

            cookies: dict = cookie_cache

    # Open the browser and login to Confluence to get the cookies
    if cookie_cache is False:
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
    
    if verbose and cookie_cache is False:
        print(f'Browser setup took {time.time() - browser_start_time:.2f} seconds.')
        print('Checking pages...')

    scan_session: requests.Session = requests.Session() # Create a session to use the cookies

    # Save the cookies to the cache
    if cookie_cache is False and cookies is not False and master_key is not None:
        try:
            with open(cookie_path, 'wb') as file:
                file.write(data_manager.encrypt_data(json.dumps(cookies), master_key))
        except:
            if verbose:
                print('Failed to save the cookies.')

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
        session: requests.Session = requests.Session()
        session.cookies.update(scan_session.cookies)

        if verbose:
            print(f'Starting thread {i}...')

        thread: threading.Thread = threading.Thread(target=scrape_thread, args=(i, session, headers, page_chunks[i], confluence_info, default_card_panel_name, card_info_skip, link_ignore_types, ignore_links, timeout, export, export_path, verbose))
        threads.append(thread)
        thread.start()
    
    if verbose:
        info_thread_thread: threading.Thread = threading.Thread(target=info_thread)
        info_thread_thread.start()
    
    for thread in threads:
        thread.join()
    
    if verbose:
        info_thread_thread.join()
    
    if log:
        generate_log(thread_info, logs_path, verbose)

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

    parser.add_argument('-d', '--data', type=str, help='The path to the data directory.')
    parser.add_argument('-q', '--query', type=str, help='The path to a queryJSON file.')
    parser.add_argument('-head', '--headers', type=str, help='The path to the headers file.')
    parser.add_argument('-c', '--count', type=int, help='The max number of pages to check.', default=250)
    parser.add_argument('-t', '--threads', type=int, help='The number of threads to use.', default=1)
    parser.add_argument('-s', '--spaces', type=str, help='The spaces to check. (e.g., "space1,space2")')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode.')
    parser.add_argument('-e', '--export', action='store_true', help='Export the pages to word documents.')
    parser.add_argument('-l', '--log', action='store_true', help='Generate a log of the failed links.')
    parser.add_argument('-op', '--out_path', type=str, help='The path to the out data (logs and exports). Defaults to directory program is run in.')
    parser.add_argument('-cache', '--cache', action='store_true', help='Use the cache.')
    parser.add_argument('-cache_path', '--cache_path', type=str, help='The path to the cache.')
    parser.add_argument('-p', '--password', type=str, help='The master password to encrypt and decrypt the cache.')
    parser.add_argument('-fp', '--forgot_password', action='store_true', help='Forgot the master password.')

    args: argparse.Namespace = parser.parse_args()

    # One of the most important paths
    data_path: str = f'.{os.sep}data{os.sep}'

    if args.data:
        data_path = args.data
    
    if not data_path.endswith(os.sep):
        data_path += os.sep
    
    # One of the most important paths
    out_path: str = f'.{os.sep}out{os.sep}'

    if args.out_path:
        out_path = args.out_path

    if not out_path.endswith(os.sep):
        out_path += os.sep

    # One of the most important paths
    cache_path: str = f'{data_path}cache{os.sep}'

    if args.cache_path:
        cache_path = args.cache_path

    if not cache_path.endswith(os.sep):
        cache_path += os.sep

    # One of the most important paths
    header_path: str = f'{data_path}headers.json'

    if args.headers:
        header_path = args.headers

    export_path: str = f'{out_path}export{os.sep}'
    logs_path: str = f'{out_path}logs{os.sep}'

    cookie_cache: bool | dict = False

    default_info_path: str = f'.{data_path}default_info.json'
    info_path: str = f'{data_path}info.json'

    query_path: str = f'{data_path}pages_query.json'

    cookie_path: str = f'{cache_path}cookies.enc'

    master_key: bytes | None = None

    if args.query:
        query_path = args.query
    
    if not os.path.exists(data_path):
        os.makedirs(out_path)
        print('Failed to find the data directory. Created the directory.')
    
    if not os.path.exists(info_path):
        print(f'Failed to find the info file at {info_path}.')

        if os.path.exists(default_info_path):
            shutil.copy(default_info_path, info_path)

            print(f'Copied the default info file to {info_path}. Go add the Confluence info!')
            exit(1)
            
        else:
            print('Failed to find the default info file.')
            exit(1)
    
    if os.path.exists(info_path) and os.path.exists(query_path):
        data: dict = data_manager.load_json(info_path)
        query: dict = data_manager.load_json(query_path)
    else:
        print('Failed to load the JSON files.')
        exit(1)
    
    if os.path.exists(header_path):
        headers: dict = data_manager.load_json(header_path)
    else:
        headers = {}
        print('Failed to load the headers file.')
    
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    if not args.spaces and data.get('confluence_info', {}).get('spaces', None) is None:
        print('Please specify the spaces to check.')
        exit(1)

    if args.spaces:
        spaces = args.spaces.split(',')

        if spaces == ['']:
            print('Please specify the spaces to check.')
            exit(1)

        data['confluence_info']['spaces'] = spaces

    if args.cache:
        if data.get('master_password', None) is not None:
            master_password: str | None = data.get('master_password', None)
        elif args.password is not None:
            master_password: str | None = args.password
        else:
            master_password: str | None = getpass.getpass('Please enter the master password: ') #Hide the password while typing
        
        if master_password is None:
            print('Caching requires a master password.')
            exit(1)
        
        master_key: bytes | None = data_manager.generate_key(master_password)

        master_password: str | None = None # Clear the master password

        if args.forgot_password and os.path.exists(cookie_path):
            os.remove(cookie_path)
            print('Deleted the cache.')
        
        if not os.path.exists(f'{cookie_path}'):
            with open(f'{cookie_path}', 'wb') as file:
                file.write(data_manager.encrypt_data(json.dumps([]), master_key))
            
        try:
            cookie_cache_raw = data_manager.decrypt_data(open(cookie_path).read(), master_key)
            cookie_cache = json.loads(cookie_cache_raw)

        except Exception as error:
            print('Failed to load the cache.')

            if args.verbose:
                print(f'error: {error}')
            
            cookie_cache = False # Just to make sure it's set to False

    thread_info: dict = {} # Define here!

    main(data, query, headers, args.count, args.threads, args.export, export_path, args.log, logs_path, cookie_cache, cookie_path, master_key, args.verbose)