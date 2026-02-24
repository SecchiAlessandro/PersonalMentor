[Skip to main content](https://docs.firecrawl.dev/introduction#content-area)

[Firecrawl Docs home page![light logo](https://mintcdn.com/firecrawl/iilnMwCX-8eR1yOO/logo/logo.png?fit=max&auto=format&n=iilnMwCX-8eR1yOO&q=85&s=c45b3c967c19a39190e76fe8e9c2ed5a)![dark logo](https://mintcdn.com/firecrawl/iilnMwCX-8eR1yOO/logo/logo-dark.png?fit=max&auto=format&n=iilnMwCX-8eR1yOO&q=85&s=3fee4abe033bd3c26e8ad92043a91c17)](https://firecrawl.dev/)

v2
![US](https://d3gk2c5xim1je2.cloudfront.net/flags/US.svg)

English

Search...

Ctrl K

Search...

Navigation

Get Started

Quickstart

[Documentation](https://docs.firecrawl.dev/introduction) [SDKs](https://docs.firecrawl.dev/sdks/overview) [Integrations](https://www.firecrawl.dev/app) [API Reference](https://docs.firecrawl.dev/api-reference/v2-introduction)

- [Playground](https://firecrawl.dev/playground)
- [Blog](https://firecrawl.dev/blog)
- [Community](https://discord.gg/gSmWdAkdwd)
- [Changelog](https://firecrawl.dev/changelog)

##### Get Started

- [Quickstart](https://docs.firecrawl.dev/introduction)
- [MCP Server](https://docs.firecrawl.dev/mcp-server)
- [Skill + CLI](https://docs.firecrawl.dev/sdks/cli)
- [Rate Limits](https://docs.firecrawl.dev/rate-limits)
- [Advanced Scraping Guide](https://docs.firecrawl.dev/advanced-scraping-guide)

##### New Features

- [Browser Sandbox](https://docs.firecrawl.dev/features/browser)
- Agent (Research Preview)


##### Standard Features

- Scrape

- [Search](https://docs.firecrawl.dev/features/search)
- [Map](https://docs.firecrawl.dev/features/map)
- [Crawl](https://docs.firecrawl.dev/features/crawl)

##### Developer Guides

- [OpenClaw](https://docs.firecrawl.dev/developer-guides/openclaw)
- [Full-Stack Templates](https://docs.firecrawl.dev/developer-guides/examples)
- Usage Guides

- LLM SDKs and Frameworks

- Cookbooks

- MCP Setup Guides

- Common Sites

- Workflow Automation


##### Webhooks

- [Overview](https://docs.firecrawl.dev/webhooks/overview)
- [Event Types](https://docs.firecrawl.dev/webhooks/events)
- [Security](https://docs.firecrawl.dev/webhooks/security)
- [Testing](https://docs.firecrawl.dev/webhooks/testing)

##### Use Cases

- [Overview](https://docs.firecrawl.dev/use-cases/overview)
- [AI Platforms](https://docs.firecrawl.dev/use-cases/ai-platforms)
- [Lead Enrichment](https://docs.firecrawl.dev/use-cases/lead-enrichment)
- [SEO Platforms](https://docs.firecrawl.dev/use-cases/seo-platforms)
- [Deep Research](https://docs.firecrawl.dev/use-cases/deep-research)
- View more


##### Contributing

- [Open Source vs Cloud](https://docs.firecrawl.dev/contributing/open-source-or-cloud)
- [Running locally](https://docs.firecrawl.dev/contributing/guide)
- [Self-hosting](https://docs.firecrawl.dev/contributing/self-host)

On this page

- [Scrape your first website](https://docs.firecrawl.dev/introduction#scrape-your-first-website)
- [Use Firecrawl with AI agents (recommended)](https://docs.firecrawl.dev/introduction#use-firecrawl-with-ai-agents-recommended)
- [Make your first request](https://docs.firecrawl.dev/introduction#make-your-first-request)
- [What can Firecrawl do?](https://docs.firecrawl.dev/introduction#what-can-firecrawl-do)
- [Why Firecrawl?](https://docs.firecrawl.dev/introduction#why-firecrawl)
- [Scraping](https://docs.firecrawl.dev/introduction#scraping)
- [Search](https://docs.firecrawl.dev/introduction#search)
- [Agent](https://docs.firecrawl.dev/introduction#agent)
- [Resources](https://docs.firecrawl.dev/introduction#resources)

![Firecrawl](https://docs.firecrawl.dev/logo/light.svg)![Firecrawl](https://docs.firecrawl.dev/logo/dark.svg)

### Ready to build?

Start getting web data for free and scale seamlessly as your project expands. **No credit card needed.**

[Start for free](https://www.firecrawl.dev/signin?utm_source=firecrawl_docs&utm_medium=docs_card&utm_content=start_for_free) [See our plans](https://www.firecrawl.dev/pricing?utm_source=firecrawl_docs&utm_medium=docs_card&utm_content=see_our_plans)

## [​](https://docs.firecrawl.dev/introduction\#scrape-your-first-website)  Scrape your first website

Turn any website into clean, LLM-ready data with a single API call.

[**Get your API key** \\
\\
Sign up and get your API key to start scraping](https://www.firecrawl.dev/app/api-keys) [**Try it in the Playground** \\
\\
Test the API instantly without writing any code](https://www.firecrawl.dev/playground)

### [​](https://docs.firecrawl.dev/introduction\#use-firecrawl-with-ai-agents-recommended)  Use Firecrawl with AI agents (recommended)

The Firecrawl skill is the fastest way for agents to discover and use Firecrawl. Without it, your agent will not know Firecrawl is available.

Copy

```
npx -y firecrawl-cli@latest init --all --browser
```

Restart your agent after installing the skill. See [Skill + CLI](https://docs.firecrawl.dev/sdks/cli) for the full setup.

Or use the [MCP Server](https://docs.firecrawl.dev/mcp-server) to connect Firecrawl directly to Claude, Cursor, Windsurf, VS Code, and other AI tools.

### [​](https://docs.firecrawl.dev/introduction\#make-your-first-request)  Make your first request

Copy the code below, replace `fc-YOUR-API-KEY` with your API key, and run it:

cURL

Python

Node

CLI

Copy

```
curl -X POST 'https://api.firecrawl.dev/v2/scrape' \
  -H 'Authorization: Bearer fc-YOUR-API-KEY' \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://example.com"}'
```

Example response

Copy

```
{
  "success": true,
  "data": {
    "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples...",
    "metadata": {
      "title": "Example Domain",
      "sourceURL": "https://example.com"
    }
  }
}
```

* * *

## [​](https://docs.firecrawl.dev/introduction\#what-can-firecrawl-do)  What can Firecrawl do?

[**Scrape** \\
\\
Extract content from any URL in markdown, HTML, or structured JSON](https://docs.firecrawl.dev/introduction#scraping) [**Search** \\
\\
Search the web and get full page content from results](https://docs.firecrawl.dev/introduction#search) [**Agent** \\
\\
Autonomous web data gathering powered by AI](https://docs.firecrawl.dev/introduction#agent) [**Browser** \\
\\
Secure, sandboxed browser sessions for interactive web workflows](https://docs.firecrawl.dev/features/browser)

### [​](https://docs.firecrawl.dev/introduction\#why-firecrawl)  Why Firecrawl?

- **LLM-ready output**: Get clean markdown, structured JSON, screenshots, and more
- **Handles the hard stuff**: Proxies, anti-bot, JavaScript rendering, and dynamic content
- **Reliable**: Built for production with high uptime and consistent results
- **Fast**: Get results in seconds, optimized for high-throughput
- **Browser Sandbox**: Fully managed browser environments for agents, zero config, scales to any size
- **MCP Server**: Connect Firecrawl to any AI tool via the [Model Context Protocol](https://docs.firecrawl.dev/mcp-server)

* * *

## [​](https://docs.firecrawl.dev/introduction\#scraping)  Scraping

Scrape any URL and get its content in markdown, HTML, or other formats. See the [Scrape feature docs](https://docs.firecrawl.dev/features/scrape) for all options.

Python

Node

cURL

CLI

Copy

```
from firecrawl import Firecrawl

firecrawl = Firecrawl(api_key="fc-YOUR-API-KEY")

# Scrape a website:
doc = firecrawl.scrape("https://firecrawl.dev", formats=["markdown", "html"])
print(doc)
```

Response

SDKs will return the data object directly. cURL will return the payload exactly as shown below.

Copy

```
{
  "success": true,
  "data" : {
    "markdown": "Launch Week I is here! [See our Day 2 Release 🚀](https://www.firecrawl.dev/blog/launch-week-i-day-2-doubled-rate-limits)[💥 Get 2 months free...",\
    "html": "<!DOCTYPE html><html lang=\"en\" class=\"light\" style=\"color-scheme: light;\"><body class=\"__variable_36bd41 __variable_d7dc5d font-inter ...",\
    "metadata": {\
      "title": "Home - Firecrawl",\
      "description": "Firecrawl crawls and converts any website into clean markdown.",\
      "language": "en",\
      "keywords": "Firecrawl,Markdown,Data,Mendable,Langchain",\
      "robots": "follow, index",\
      "ogTitle": "Firecrawl",\
      "ogDescription": "Turn any website into LLM-ready data.",\
      "ogUrl": "https://www.firecrawl.dev/",\
      "ogImage": "https://www.firecrawl.dev/og.png?123",\
      "ogLocaleAlternate": [],\
      "ogSiteName": "Firecrawl",\
      "sourceURL": "https://firecrawl.dev",\
      "statusCode": 200\
    }\
  }\
}\
```\
\
## [​](https://docs.firecrawl.dev/introduction\#search)  Search\
\
Firecrawl’s search API allows you to perform web searches and optionally scrape the search results in one operation.\
\
- Choose specific output formats (markdown, HTML, links, screenshots)\
- Choose specific sources (web, news, images)\
- Search the web with customizable parameters (location, etc.)\
\
For details, see the [Search Endpoint API Reference](https://docs.firecrawl.dev/api-reference/endpoint/search).\
\
Python\
\
Node\
\
CLI\
\
Copy\
\
```\
from firecrawl import Firecrawl\
\
firecrawl = Firecrawl(api_key="fc-YOUR-API-KEY")\
\
results = firecrawl.search(\
    query="firecrawl",\
    limit=3,\
)\
print(results)\
```\
\
Response\
\
SDKs will return the data object directly. cURL will return the complete payload.\
\
JSON\
\
Copy\
\
```\
{\
  "success": true,\
  "data": {\
    "web": [\
      {\
        "url": "https://www.firecrawl.dev/",\
        "title": "Firecrawl - The Web Data API for AI",\
        "description": "The web crawling, scraping, and search API for AI. Built for scale. Firecrawl delivers the entire internet to AI agents and builders.",\
        "position": 1\
      },\
      {\
        "url": "https://github.com/firecrawl/firecrawl",\
        "title": "mendableai/firecrawl: Turn entire websites into LLM-ready ... - GitHub",\
        "description": "Firecrawl is an API service that takes a URL, crawls it, and converts it into clean markdown or structured data.",\
        "position": 2\
      },\
      ...\
    ],\
    "images": [\
      {\
        "title": "Quickstart | Firecrawl",\
        "imageUrl": "https://mintlify.s3.us-west-1.amazonaws.com/firecrawl/logo/logo.png",\
        "imageWidth": 5814,\
        "imageHeight": 1200,\
        "url": "https://docs.firecrawl.dev/",\
        "position": 1\
      },\
      ...\
    ],\
    "news": [\
      {\
        "title": "Y Combinator startup Firecrawl is ready to pay $1M to hire three AI agents as employees",\
        "url": "https://techcrunch.com/2025/05/17/y-combinator-startup-firecrawl-is-ready-to-pay-1m-to-hire-three-ai-agents-as-employees/",\
        "snippet": "It's now placed three new ads on YC's job board for “AI agents only” and has set aside a $1 million budget total to make it happen.",\
        "date": "3 months ago",\
        "position": 1\
      },\
      ...\
    ]\
  }\
}\
```\
\
## [​](https://docs.firecrawl.dev/introduction\#agent)  Agent\
\
Firecrawl’s Agent is an autonomous web data gathering tool. Just describe what data you need, and it will search, navigate, and extract it from anywhere on the web. See the [Agent feature docs](https://docs.firecrawl.dev/features/agent) for all options.\
\
cURL\
\
Python\
\
Node\
\
Copy\
\
```\
curl -X POST 'https://api.firecrawl.dev/v2/agent' \\
  -H 'Authorization: Bearer fc-YOUR-API-KEY' \\
  -H 'Content-Type: application/json' \\
  -d '{\
    "prompt": "Find the pricing plans for Notion"\
  }'\
```\
\
Example response\
\
Copy\
\
```\
{\
  "success": true,\
  "data": {\
    "result": "Notion offers the following pricing plans:\n\n1. **Free** - $0/month - For individuals...\n2. **Plus** - $10/seat/month - For small teams...\n3. **Business** - $18/seat/month - For companies...\n4. **Enterprise** - Custom pricing - For large organizations...",\
    "sources": [\
      "https://www.notion.so/pricing"\
    ]\
  }\
}\
```\
\
* * *\
\
## [​](https://docs.firecrawl.dev/introduction\#resources)  Resources\
\
[**API Reference** \\
\\
Complete API documentation with interactive examples](https://docs.firecrawl.dev/api-reference/v2-introduction) [**SDKs** \\
\\
Python, Node.js, CLI, and community SDKs](https://docs.firecrawl.dev/sdks/overview) [**Open Source** \\
\\
Self-host Firecrawl or contribute to the project](https://docs.firecrawl.dev/contributing/open-source-or-cloud) [**Integrations** \\
\\
LangChain, LlamaIndex, OpenAI, and more](https://docs.firecrawl.dev/developer-guides/llm-sdks-and-frameworks/openai)\
\
[Suggest edits](https://github.com/firecrawl/firecrawl-docs/edit/main/introduction.mdx) [Raise issue](https://github.com/firecrawl/firecrawl-docs/issues/new?title=Issue%20on%20docs&body=Path:%20/introduction)\
\
[Firecrawl MCP Server\\
\\
Next](https://docs.firecrawl.dev/mcp-server)\
\
Chat Widget\
\
Loading...