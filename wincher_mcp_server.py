import os
import sys
import ipaddress
import asyncio
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Initialize the MCP server
app = Server("wincher-mcp")

# Production API host (public). Staging host is never stored in source; see WINCHER_STAGING_API_HOST.
PRODUCTION_BASE_URL = "https://api.wincher.com"

# Limits aligned with Wincher API docs / OpenAPI (rate limit 5000 req/hour; bulk maxItems in spec).
MAX_BULK_KEYWORD_IDS = 1000
MAX_FORMAT_ROWS = 500
HTTP_TIMEOUT_SECONDS = 30.0

_BLOCKED_STAGING_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "169.254.169.254",
        "metadata.google.internal",
    }
)

# MCP registration only (add to the server args array). Not environment variables.
_USE_STAGING = "--use-staging" in sys.argv
_USE_TOON = "--use-toon" in sys.argv

_TOON_PREAMBLE = (
    "Format: TOON (Token-Oriented Object Notation). "
    "Decode with: from toon import decode. "
    "Spec: https://github.com/toon-format/toon\n\n"
)

_OUTPUT_FORMAT_PROPERTY = {
    "output_format": {
        "type": "string",
        "enum": ["text", "toon"],
        "description": (
            "Response encoding. Default is human-readable text, or TOON when the server "
            "is started with --use-toon. TOON uses fewer tokens for large tabular results."
        ),
    }
}


def use_staging_enabled() -> bool:
    return _USE_STAGING


def use_toon_enabled() -> bool:
    return _USE_TOON


def _tool_input_schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {**properties, **_OUTPUT_FORMAT_PROPERTY},
        "required": required,
    }


def _resolve_output_format(arguments: dict) -> str:
    fmt = arguments.get("output_format")
    if fmt is None:
        return "toon" if use_toon_enabled() else "text"
    if fmt not in ("text", "toon"):
        raise ValueError('output_format must be "text" or "toon"')
    return fmt


def _cap_items(items: list) -> tuple[list, bool]:
    if len(items) <= MAX_FORMAT_ROWS:
        return items, False
    return items[:MAX_FORMAT_ROWS], True


def _encode_toon(payload: dict) -> str:
    try:
        from toon import encode
    except ImportError as e:
        raise ValueError(
            "TOON output requires the python-toon package (pip install python-toon)"
        ) from e
    return encode(payload)


def _render_tool_output(
    *,
    output_format: str,
    title: str,
    items: list,
    text_formatter,
    label: str,
    meta: dict | None = None,
    data_key: str = "data",
) -> str:
    """Human-readable text (default) or compact TOON for LLM context."""
    capped, truncated = _cap_items(items)
    if output_format == "text":
        return title + _format_rows(capped, text_formatter, label=label)

    payload: dict = {data_key: capped}
    meta_block = dict(meta or {})
    meta_block["returned"] = len(capped)
    meta_block["total"] = len(items)
    if truncated:
        meta_block["truncated"] = True
    payload["meta"] = meta_block
    return _TOON_PREAMBLE + title.strip() + "\n\n" + _encode_toon(payload)


def _api_key() -> str:
    if use_staging_enabled():
        key = (os.getenv("WINCHER_STAGING_API_KEY") or os.getenv("WINCHER_API_KEY") or "").strip()
        if not key:
            raise ValueError(
                "WINCHER_STAGING_API_KEY (or WINCHER_API_KEY) environment variable not set"
            )
        return key
    key = (os.getenv("WINCHER_API_KEY") or "").strip()
    if not key:
        raise ValueError("WINCHER_API_KEY environment variable not set")
    return key


def _api_path(relative: str) -> str:
    """Build versioned API path. Staging host often omits the /v1 prefix in the base URL."""
    rel = relative.lstrip("/")
    base = base_url().rstrip("/")
    if use_staging_enabled() and not base.endswith("/v1"):
        return f"/{rel}"
    return f"/v1/{rel}"


def _validate_api_base_url(url: str, *, staging: bool) -> str:
    """Reject non-HTTPS and unsafe staging targets (SSRF hardening)."""
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        raise ValueError("API base URL must use HTTPS")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("API base URL is invalid")
    if staging:
        if hostname.lower() in _BLOCKED_STAGING_HOSTS:
            raise ValueError("Staging API host is not allowed")
        try:
            addr = ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            if (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved
            ):
                raise ValueError("Staging API host is not allowed")
    port = f":{parsed.port}" if parsed.port else ""
    return f"https://{hostname}{port}{parsed.path or ''}".rstrip("/")


def base_url() -> str:
    if use_staging_enabled():
        host = (os.getenv("WINCHER_STAGING_API_HOST") or "").strip()
        if not host:
            raise ValueError(
                "Staging is enabled (--use-staging in MCP args) but WINCHER_STAGING_API_HOST is not set"
            )
        return _validate_api_base_url(host, staging=True)
    return _validate_api_base_url(PRODUCTION_BASE_URL, staging=False)


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _positive_int_list(name: str, values: object, *, max_items: int) -> list[int]:
    if not isinstance(values, list):
        raise ValueError(f"{name} must be an array of integers")
    if len(values) > max_items:
        raise ValueError(f"{name} must contain at most {max_items} items")
    return [_positive_int(name, item) for item in values]


def _format_rows(items: list, formatter, *, label: str) -> str:
    """Cap rows returned to the MCP host to limit context and memory use."""
    lines: list[str] = []
    for item in items[:MAX_FORMAT_ROWS]:
        lines.append(formatter(item))
    if len(items) > MAX_FORMAT_ROWS:
        lines.append(
            f"\n(Showing {MAX_FORMAT_ROWS} of {len(items)} {label}. Narrow filters or use bulk with fewer IDs.)"
        )
    return "".join(lines)


def _auth_headers(*, json_body: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Accept": "application/json",
    }
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _format_http_error(error: httpx.HTTPStatusError, endpoint: str) -> str:
    lines = [
        f"API Error: {error.response.status_code}",
        f"Endpoint: {endpoint}",
    ]
    body = (error.response.text or "").strip()
    if body:
        snippet = body if len(body) <= 200 else f"{body[:200]}..."
        lines.append(f"Message: {snippet}")
    return "\n".join(lines)


async def wincher_request(
    method: str,
    endpoint: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """Authenticated Wincher API request (GET or POST)."""
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    url = f"{base_url()}{endpoint}"
    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await client.request(
            method.upper(),
            url,
            headers=_auth_headers(json_body=json_body is not None),
            params=params,
            json=json_body,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()


async def make_wincher_request(endpoint: str, params: dict | None = None) -> dict:
    return await wincher_request("GET", endpoint, params=params)

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Wincher API tools"""
    return [
        Tool(
            name="get_websites",
            description="List all websites tracked in your Wincher account with keyword counts and competitor information",
            inputSchema=_tool_input_schema({}, []),
        ),
        Tool(
            name="get_keywords",
            description="Get all keywords for a specific website with current rankings, search volume, and related fields returned by the API",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website (get from get_websites)",
                    }
                },
                ["website_id"],
            ),
        ),
        Tool(
            name="get_keyword_rankings",
            description="Get detailed ranking history for a specific keyword over time",
            inputSchema=_tool_input_schema(
                {
                    "keyword_id": {
                        "type": "integer",
                        "description": "The ID of the keyword (get from get_keywords)",
                    },
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    },
                },
                ["keyword_id", "website_id"],
            ),
        ),
        Tool(
            name="get_competitor_ranking_summaries",
            description="Get ranking summary comparison between your website and all tracked competitors including traffic, share of voice, and position distribution",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    }
                },
                ["website_id"],
            ),
        ),
        Tool(
            name="get_competitor_keyword_positions",
            description="Get detailed keyword-by-keyword position comparison between your website and competitors",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    }
                },
                ["website_id"],
            ),
        ),
        Tool(
            name="get_serps",
            description="Get SERP (Search Engine Results Page) data for a keyword showing who ranks in top positions and what SERP features are present",
            inputSchema=_tool_input_schema(
                {
                    "keyword_id": {
                        "type": "integer",
                        "description": "The ID of the keyword",
                    },
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    },
                },
                ["keyword_id", "website_id"],
            ),
        ),
        Tool(
            name="get_keyword_groups",
            description="List all keyword groups for a website with their aggregate performance metrics",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    }
                },
                ["website_id"],
            ),
        ),
        Tool(
            name="get_bulk_ranking_history",
            description="Get historical ranking data for multiple keywords at once (more efficient than getting them one by one)",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    },
                    "keyword_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Array of keyword IDs to get history for",
                    },
                    "start_at": {
                        "type": "string",
                        "description": "Start date in ISO-8601 format (e.g., 2024-01-01T00:00:00Z)",
                    },
                    "end_at": {
                        "type": "string",
                        "description": "End date in ISO-8601 format (e.g., 2024-12-31T23:59:59Z)",
                    },
                },
                ["website_id", "keyword_ids", "start_at", "end_at"],
            ),
        ),
        Tool(
            name="get_annotations",
            description="Get annotations (notes about SEO activities, ranking changes, etc.) for a website",
            inputSchema=_tool_input_schema(
                {
                    "website_id": {
                        "type": "integer",
                        "description": "The ID of the website",
                    }
                },
                ["website_id"],
            ),
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls to Wincher API"""
    endpoint = "unknown"

    try:
        output_format = _resolve_output_format(arguments)

        if name == "get_websites":
            endpoint = _api_path("websites")
            data = await make_wincher_request(endpoint)
            def format_site(site: dict) -> str:
                block = (
                    f"ID: {site.get('id', 'N/A')}\n"
                    f"Domain: {site.get('domain', 'N/A')}\n"
                )
                search_engine = site.get("search_engine", {})
                block += f"Search Engine: {search_engine.get('domain', 'N/A')}\n"
                location = site.get("location", {})
                block += f"Location: {location.get('name', 'N/A')} ({location.get('code', 'N/A')})\n"
                block += f"Language: {site.get('language', 'N/A')}\n"
                block += f"Keywords: {site.get('keyword_count', 0)}\n"
                block += f"Competitors: {site.get('competitor_count', 0)}\n"
                block += f"Mobile: {site.get('is_mobile', False)}\n"
                competitors = site.get("competitors", [])
                if competitors:
                    comp_domains = [c.get("domain", "") for c in competitors]
                    block += f"Tracking: {', '.join(comp_domains)}\n"
                return block + "\n"

            result = _render_tool_output(
                output_format=output_format,
                title="Tracked Websites:\n\n",
                items=data.get("data", []),
                text_formatter=format_site,
                label="websites",
                meta={"tool": "get_websites"},
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_keywords":
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/keywords")
            data = await make_wincher_request(endpoint)

            def format_keyword(kw: dict) -> str:
                return (
                    f"ID: {kw.get('id', 'N/A')}\n"
                    f"Keyword: {kw.get('keyword', 'N/A')}\n"
                    f"Current Rank: {kw.get('position', 'N/A')}\n"
                    f"Previous Rank: {kw.get('previous_position', 'N/A')}\n"
                    f"Best Rank: {kw.get('best_position', 'N/A')}\n"
                    f"Search Volume: {kw.get('search_volume', 'N/A')}\n"
                    f"URL: {kw.get('url', 'N/A')}\n"
                    f"Last Updated: {kw.get('updated_at', 'N/A')}\n\n"
                )

            result = _render_tool_output(
                output_format=output_format,
                title=f"Keywords for Website ID {website_id}:\n\n",
                items=data.get("data", []),
                text_formatter=format_keyword,
                label="keywords",
                meta={"tool": "get_keywords", "website_id": website_id},
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_keyword_rankings":
            keyword_id = _positive_int("keyword_id", arguments["keyword_id"])
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/keyword/{keyword_id}/ranking-history")
            data = await make_wincher_request(endpoint)
            
            def format_series(series: dict) -> str:
                block = ""
                if series.get("label"):
                    block += f"Series: {series['label']}\n"
                for point in series.get("data", [])[:MAX_FORMAT_ROWS]:
                    block += f"Date: {point.get('date', 'N/A')}\n"
                    block += f"Position: {point.get('position', 'N/A')}\n"
                    if point.get("url"):
                        block += f"URL: {point['url']}\n"
                    block += "\n"
                return block

            result = _render_tool_output(
                output_format=output_format,
                title=f"Ranking History for Keyword ID {keyword_id}:\n\n",
                items=data.get("data", []),
                text_formatter=format_series,
                label="series",
                meta={
                    "tool": "get_keyword_rankings",
                    "website_id": website_id,
                    "keyword_id": keyword_id,
                },
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_competitor_ranking_summaries":
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/competitors/ranking-summaries")
            data = await make_wincher_request(endpoint)
            
            def format_summary(summary: dict) -> str:
                ranking = summary.get("ranking", {})
                avg_pos = ranking.get("avg_position", {})
                traffic = ranking.get("traffic", {})
                sov = ranking.get("share_of_voice", {})
                volume = ranking.get("volume", {})
                return (
                    f"Domain: {summary.get('domain', 'N/A')}\n"
                    f"Is Your Website: {summary.get('is_tracked_website', False)}\n"
                    f"Average Position: {avg_pos.get('value', 'N/A')}\n"
                    f"Position Change: {avg_pos.get('change', 'N/A')}\n"
                    f"Estimated Traffic: {traffic.get('value', 'N/A')}\n"
                    f"Share of Voice: {sov.get('value', 'N/A')}%\n"
                    f"Total Search Volume: {volume.get('value', 'N/A')}\n\n"
                )

            result = _render_tool_output(
                output_format=output_format,
                title="Competitor Ranking Comparison:\n\n",
                items=data.get("data", []),
                text_formatter=format_summary,
                label="summaries",
                meta={"tool": "get_competitor_ranking_summaries", "website_id": website_id},
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_competitor_keyword_positions":
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/competitors/keyword-positions")
            data = await make_wincher_request(endpoint)
            
            def format_position_row(item: dict) -> str:
                block = (
                    f"Keyword: {item.get('keyword', 'N/A')}\n"
                    f"Search Volume: {item.get('volume', 'N/A')}\n"
                )
                for pos in item.get("positions", []):
                    line = f"  • {pos.get('domain', 'N/A')}: Position {pos.get('position', 'N/A')}"
                    if pos.get("is_tracked_website"):
                        line += " (YOUR SITE)"
                    block += line + "\n"
                return block + "\n"

            result = _render_tool_output(
                output_format=output_format,
                title="Keyword Position Comparison:\n\n",
                items=data.get("data", []),
                text_formatter=format_position_row,
                label="keywords",
                meta={"tool": "get_competitor_keyword_positions", "website_id": website_id},
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_serps":
            keyword_id = _positive_int("keyword_id", arguments["keyword_id"])
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/keywords/{keyword_id}/serps")
            data = await make_wincher_request(endpoint)
            
            def format_serp(serp: dict) -> str:
                block = (
                    f"Date: {serp.get('date', 'N/A')}\n"
                    f"Search Volume: {serp.get('volume', {}).get('value', 'N/A')}\n"
                )
                features = serp.get("features", [])
                if features:
                    block += f"SERP Features: {', '.join(features)}\n"
                block += "\nTop Rankings:\n"
                for i, res in enumerate(serp.get("results", [])[:10], 1):
                    block += f"{i}. {res.get('domain', 'N/A')}\n"
                    block += f"   Title: {res.get('title', 'N/A')[:80]}...\n"
                    if res.get("url"):
                        block += f"   URL: {res['url']}\n"
                return block + "\n"

            result = _render_tool_output(
                output_format=output_format,
                title=f"SERP Data for Keyword ID {keyword_id}:\n\n",
                items=data.get("data", []),
                text_formatter=format_serp,
                label="SERP snapshots",
                meta={
                    "tool": "get_serps",
                    "website_id": website_id,
                    "keyword_id": keyword_id,
                },
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_keyword_groups":
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/groups")
            data = await make_wincher_request(endpoint)
            
            def format_group(group: dict) -> str:
                ranking = group.get("ranking", {})
                avg_pos = ranking.get("avg_position", {})
                traffic = ranking.get("traffic", {})
                volume = ranking.get("volume", {})
                return (
                    f"Group: {group.get('name', 'N/A')}\n"
                    f"Keywords: {len(group.get('keyword_ids', []))}\n"
                    f"Average Position: {avg_pos.get('value', 'N/A')}\n"
                    f"Estimated Traffic: {traffic.get('value', 'N/A')}\n"
                    f"Total Search Volume: {volume.get('value', 'N/A')}\n"
                    f"Average Difficulty: {group.get('avg_keyword_difficulty', 'N/A')}\n\n"
                )

            result = _render_tool_output(
                output_format=output_format,
                title="Keyword Groups:\n\n",
                items=data.get("data", []),
                text_formatter=format_group,
                label="groups",
                meta={"tool": "get_keyword_groups", "website_id": website_id},
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_bulk_ranking_history":
            website_id = _positive_int("website_id", arguments["website_id"])
            keyword_ids = _positive_int_list(
                "keyword_ids",
                arguments["keyword_ids"],
                max_items=MAX_BULK_KEYWORD_IDS,
            )
            start_at = arguments["start_at"]
            end_at = arguments["end_at"]
            if not isinstance(start_at, str) or not isinstance(end_at, str):
                raise ValueError("start_at and end_at must be ISO-8601 date strings")
            
            payload = {
                "keyword_ids": keyword_ids,
                "start_at": start_at,
                "end_at": end_at
            }

            endpoint = _api_path(f"websites/{website_id}/ranking-history")
            data = await wincher_request("POST", endpoint, json_body=payload)
            
            def format_bulk_item(item: dict) -> str:
                block = (
                    f"Keyword ID: {item.get('keyword_id', 'N/A')}\n"
                    f"Keyword: {item.get('keyword', 'N/A')}\n"
                )
                for point in item.get("data", []):
                    block += (
                        f"  {point.get('date', 'N/A')}: Position {point.get('position', 'N/A')}\n"
                    )
                return block + "\n"

            result = _render_tool_output(
                output_format=output_format,
                title=f"Bulk Ranking History ({start_at} to {end_at}):\n\n",
                items=data.get("data", []),
                text_formatter=format_bulk_item,
                label="keywords",
                meta={
                    "tool": "get_bulk_ranking_history",
                    "website_id": website_id,
                    "start_at": start_at,
                    "end_at": end_at,
                },
            )
            return [TextContent(type="text", text=result)]

        elif name == "get_annotations":
            website_id = _positive_int("website_id", arguments["website_id"])
            endpoint = _api_path(f"websites/{website_id}/annotations")
            data = await make_wincher_request(endpoint)
            
            def format_annotation(annotation: dict) -> str:
                block = (
                    f"Date: {annotation.get('date', 'N/A')}\n"
                    f"Type: {annotation.get('type', 'N/A')}\n"
                    f"Description: {annotation.get('description', 'N/A')}\n"
                )
                author = annotation.get("author", {})
                if author.get("profile"):
                    author_name = (
                        f"{author['profile'].get('first_name', '')} "
                        f"{author['profile'].get('last_name', '')}"
                    )
                    block += f"Author: {author_name.strip()}\n"
                return block + "\n"

            result = _render_tool_output(
                output_format=output_format,
                title="Annotations:\n\n",
                items=data.get("data", []),
                text_formatter=format_annotation,
                label="annotations",
                meta={"tool": "get_annotations", "website_id": website_id},
            )
            return [TextContent(type="text", text=result)]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=_format_http_error(e, endpoint))]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
