## Basics

Please refer to the [readme.md](/readme.md) for the basics of running the project, including:
- Optional launch arguments and their functions
- How to pull the project

## Where does this project store its data?

Upon the first launch, the project will create a new folder named `confluence-crawler` within your documents directory and copy the entire data directory into it. This is to ensure that data will be retained for future versions of the software.

## Logs and Exports

The program generates logs to help you track its activities and diagnose any issues. These logs are stored in the `out` directory within the `logs` folder. The `out` directory can be located inside the `confluence-crawler` folder. Each log file is timestamped for easy identification.

Additionally, you can export the data collected by the program. The exports are saved in the `exports` directory, also within the `out` directory. You'll find them inside the `confluence-crawler` folder as well. The exported files are direct .doc downloads of each page.


## I don't have an info.json!

If the project hasn't run before, you won't have an info.json file. You can either copy the default_info.json file and rename it to info.json, or launch the project once to generate the file automatically.

## What is the master password?

The master password is used to encrypt and decrypt your cache. This ensures that only you can access your cache. If someone else obtains your cache, they will need to know your master password to use it. Dont forget it!

## Do I need to add my master password to this file?

No! The program can obtain your master password in three ways:
1. By checking the `info.json` file.
2. By passing it as a command-line argument.
3. By prompting you for it if the first two methods fail <b>(recommended, as it hides your input).</b>

## Adding Space Information

Replace each instance of "null" with the appropriate information. To find the specific `base_url` and `space` you need, visit the space and copy the base URL and space ID from your workspace link. The base URL is represented as `https://your_confluence_link_here.com` and the space ID is represented as `SPACE_GOES_HERE` in the example below.

![Your Space](/docs/images/confluence_show_space_in_link.png)

If you have more than one space, repeat the previous step for each space and add it to the list.

For one space:

```json
"spaces": ["Example"]
```

For multiple spaces:

```json
"spaces": ["Example 1", "Example 2"]
```

## What are the headers.json and pages_query.json?

The `headers.json` file contains the identifiers your computer uses when communicating with different servers. Some sites require verification that you are a real person, so the header essentially says, "I am a person using Chrome, let me in."

The `pages_query.json` file contains data extracted from Confluence. It is used to get a list of available pages by recreating the same request that Confluence's JavaScript would make.

## Reached the Login Screen?

You should see a screen similar to this:
![Login Screen](/docs/images/confluence_log_in.png)

Log in as you normally would, regardless of whether you've logged in with Jira before. (It should be fine, if not just open an Issue)