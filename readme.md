# Confluence Crawler 🕷️

## Overview

This project is a Confluence Crawler that scans Confluence pages for dead links. It helps in maintaining the integrity of your Confluence documentation by identifying and reporting broken links.

## Features

- Crawls Confluence pages to find dead links
- Generates a report of broken links

## Installation

To install the Confluence Crawler, clone the repository and install the dependencies:

```bash
git clone https://github.com/Will-Hellinger/confluence-crawler.git
cd confluence-crawler
pip install -r requirements.txt
```

## Usage

To run the crawler, use the following command:

```
python ./src/main.py -c [page count] -t [thread count]
```

## Arguments

- `-d`, `--data`: The path to the JSON data file.
- `-q`, `--query`: The path to a query JSON file.
- `-head`, `--headers`: The path to the headers file.
- `-c`, `--count`: The max number of pages to check. (default: 1000)
- `-t`, `--threads`: The number of threads to use. (default: 1)
- `-s`, `--spaces`: The spaces to check. (e.g., "space1,space2")
- `-v`, `--verbose`: Enable verbose mode.
- `-e`, `--export`: Export the pages to word documents.
- `-ep`, `--export_path`: The path to export the word documents.
- `-cache`, `--cache`: Use the cache.
- `-cache_path`, `--cache_path`: The path to the cache.

## Configuration

The crawler can be configured using a JSON file. Below is an example configuration:

- You want to replace the base_url with the link directly to your wiki site.
- The spaces should be added individually as items (make sure spelling is exact)
- If you have specifical types of links to ignore, the link_ignore_types checks the start of each link for the starting ignore type.
- Change info skip to keep track of specific info as you please.

```json
{
    "browser": "Chrome",
    "confluence_info" : {
        "base_url": null,
        "login_url" : "/wiki/spaces",
        "query_url" : "/cgraphql?q=SpacePagesQuery",
        "page_info_url" : "/wiki/pages/viewinfo.action?pageId=",
        "spaces" : []
    },
    "timeout" : 3,
    "default_card_panel_name" : "Basic Info",
    "link_ignore_types" : ["mailto", "tel", "data", "file"],
    "info_skip" : {
        "default_card_panel_name" : ["Operations", "Tiny Link: (useful for email)"],
        "Labels" : true,
        "Recent Changes" : true,
        "Incoming Links" : true,
        "Outgoing Links" : false
    }
}
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the GNU GPL V3 License. See the [LICENSE](LICENSE) file for details.