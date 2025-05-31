#!/usr/bin/env python3
import asyncio
import json
import urllib.parse
from typing import Any, Dict, List
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent


app = Server("elgov-mcp")
BASE_URL = "https://laws.e-gov.go.jp/api/2"
http_client = httpx.AsyncClient(timeout=30.0)


@app.list_tools()
async def list_tools() -> List[Tool]:
    """利用可能なツールのリストを返す"""
    law_types = ["Constitution", "Act", "CabinetOrder", "MinisterialOrdinance", "Rule"]
    eras = ["Meiji", "Taisho", "Showa", "Heisei", "Reiwa"]

    return [
        Tool(
            name="get_laws",
            description="法令一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_id": {
                        "type": "string",
                        "description": "法令ID（指定時は単一法令の詳細を取得）",
                    },
                    "law_title": {
                        "type": "string",
                        "description": "法令名での検索（部分一致）",
                    },
                    "law_type": {
                        "type": "string",
                        "enum": law_types,
                        "description": "法令種別",
                    },
                    "law_num_era": {
                        "type": "string",
                        "enum": eras,
                        "description": "法令番号の年代",
                    },
                    "law_num_year": {"type": "integer", "description": "法令番号の年"},
                    "category": {"type": "string", "description": "法令カテゴリ"},
                    "promulgation_date": {
                        "type": "string",
                        "description": "公布日（YYYY-MM-DD形式）",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "xml"],
                        "description": "取得フォーマット（デフォルト: json）",
                        "default": "json",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "取得する法令数の上限（デフォルト: 10）",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_law_data",
            description="特定の法令の本文データを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_revision_id": {"type": "string", "description": "法令履歴ID"},
                    "format": {
                        "type": "string",
                        "enum": ["json", "xml"],
                        "description": "取得フォーマット（デフォルト: json）",
                        "default": "json",
                    },
                },
                "required": ["law_revision_id"],
            },
        ),
        Tool(
            name="get_law_revisions",
            description="特定の法令の履歴一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {"law_id": {"type": "string", "description": "法令ID"}},
                "required": ["law_id"],
            },
        ),
        Tool(
            name="search_keyword",
            description="法令本文内のキーワード検索を行います",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "検索キーワード"},
                    "lawType": {
                        "type": "string",
                        "enum": law_types,
                        "description": "法令種別",
                    },
                    "promulgateEra": {
                        "type": "string",
                        "enum": eras,
                        "description": "公布年代",
                    },
                    "promulgateYear": {"type": "integer", "description": "公布年"},
                    "category": {"type": "string", "description": "法令分類"},
                    "offset": {
                        "type": "integer",
                        "description": "取得開始位置（デフォルト: 0）",
                        "default": 0,
                        "minimum": 0,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "取得数（デフォルト: 100、最大: 500）",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 500,
                    },
                },
                "required": ["keyword"],
            },
        ),
        Tool(
            name="get_attachment",
            description="法令の添付ファイルを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_revision_id": {"type": "string", "description": "法令履歴ID"},
                    "src": {"type": "string", "description": "添付ファイルのパス"},
                },
                "required": ["law_revision_id", "src"],
            },
        ),
        Tool(
            name="get_law_file",
            description="法令本文ファイルを取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_revision_id": {"type": "string", "description": "法令履歴ID"},
                    "type": {
                        "type": "string",
                        "enum": ["pdf", "docx", "xml"],
                        "description": "ファイルタイプ",
                    },
                },
                "required": ["law_revision_id", "type"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """ツールの実行"""
    try:
        if name == "get_laws":
            return await get_laws(arguments)
        elif name == "get_law_data":
            return await get_law_data(arguments)
        elif name == "get_law_revisions":
            return await get_law_revisions(arguments)
        elif name == "search_keyword":
            return await search_keyword(arguments)
        elif name == "get_attachment":
            return await get_attachment(arguments)
        elif name == "get_law_file":
            return await get_law_file(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def get_laws(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令一覧取得 - /laws エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {
        "law_id",
        "law_title",
        "law_type",
        "law_num_era",
        "law_num_year",
        "category",
        "promulgation_date",
        "format",
        "limit",
    }

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_laws で使用可能なパラメータ:\n"
            f"- law_id: 法令ID（指定時は単一法令の詳細を取得）\n"
            f"- law_title: 法令名での検索（部分一致）\n"
            f"- law_type: 法令種別 (Constitution, Act, CabinetOrder, "
            f"MinisterialOrdinance, Rule)\n"
            f"- law_num_era: 法令番号の年代 (Meiji, Taisho, Showa, "
            f"Heisei, Reiwa)\n"
            f"- law_num_year: 法令番号の年\n"
            f"- category: 法令カテゴリ\n"
            f"- promulgation_date: 公布日（YYYY-MM-DD形式）\n"
            f"- format: 取得フォーマット (json, xml)（デフォルト: json）\n"
            f"- limit: 取得する法令数の上限（デフォルト: 10）\n\n"
            f"※法令名で検索する場合は get_laws を使用してください。"
        )
        return [TextContent(type="text", text=error_msg)]

    params = {}

    # 法令一覧取得APIで有効なパラメータのみ設定
    if "law_id" in arguments:
        params["law_id"] = arguments["law_id"]
    if "law_title" in arguments:
        params["law_title"] = arguments["law_title"]
    if "law_type" in arguments:
        params["law_type"] = arguments["law_type"]
    if "law_num_era" in arguments:
        params["law_num_era"] = arguments["law_num_era"]
    if "law_num_year" in arguments:
        params["law_num_year"] = arguments["law_num_year"]
    if "category" in arguments:
        params["category"] = arguments["category"]
    if "promulgation_date" in arguments:
        params["promulgation_date"] = arguments["promulgation_date"]
    if "format" in arguments:
        params["format"] = arguments["format"]
    if "limit" in arguments:
        params["limit"] = arguments["limit"]
    else:
        params["limit"] = 10

    # 適切なURLエンコードを使用してクエリ文字列を構築
    if params:
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}/laws?{query_string}"
    else:
        url = f"{BASE_URL}/laws"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    result = response.json()
    text = debug_info + json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


async def get_law_data(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令本文取得 - /law_data エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_revision_id", "format"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_law_data で使用可能なパラメータ:\n"
            f"- law_revision_id: 法令履歴ID（必須）\n"
            f"- format: 取得フォーマット (json, xml)（デフォルト: json）\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_revision_id" not in arguments:
        return [
            TextContent(
                type="text", text="エラー: law_revision_id パラメータは必須です"
            )
        ]

    law_revision_id = arguments["law_revision_id"]
    format_type = arguments.get("format", "json")

    params = {"format": format_type}

    # 適切なURLエンコードを使用してクエリ文字列を構築
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/law_data/{law_revision_id}?{query_string}"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    if format_type == "json":
        result = response.json()
        text = debug_info + json.dumps(result, ensure_ascii=False, indent=2)
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=debug_info + response.text)]


async def get_law_revisions(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令履歴一覧取得 - /laws/{law_id}/revisions エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_id"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_law_revisions で使用可能なパラメータ:\n"
            f"- law_id: 法令ID（必須）\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_id" not in arguments:
        return [TextContent(type="text", text="エラー: law_id パラメータは必須です")]

    law_id = arguments["law_id"]

    url = f"{BASE_URL}/laws/{law_id}/revisions"
    debug_info = f"Request URL: {url}\n"

    response = await http_client.get(url)
    response.raise_for_status()

    result = response.json()
    text = debug_info + json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


async def search_keyword(arguments: Dict[str, Any]) -> List[TextContent]:
    """キーワード検索 - /keyword エンドポイント用"""
    # 有効なパラメータのリスト
    valid_params = {
        "keyword",
        "lawType",
        "promulgateEra",
        "promulgateYear",
        "category",
        "offset",
        "limit",
    }

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"search_keyword で使用可能なパラメータ:\n"
            f"- keyword: 検索キーワード（必須）\n"
            f"- lawType: 法令種別 (Constitution, Act, CabinetOrder, "
            f"MinisterialOrdinance, Rule)\n"
            f"- promulgateEra: 公布年代 (Meiji, Taisho, Showa, "
            f"Heisei, Reiwa)\n"
            f"- promulgateYear: 公布年\n"
            f"- category: 法令分類\n"
            f"- offset: 取得開始位置（デフォルト: 0）\n"
            f"- limit: 取得数（デフォルト: 100、最大: 500）\n\n"
            f"※法令名で検索する場合は get_laws を使用してください。"
        )
        return [TextContent(type="text", text=error_msg)]

    if "keyword" not in arguments:
        return [TextContent(type="text", text="エラー: keyword パラメータは必須です")]

    params = {"keyword": arguments["keyword"]}

    # キーワード検索APIで有効なパラメータのみ設定
    if "lawType" in arguments:
        params["lawType"] = arguments["lawType"]
    if "promulgateEra" in arguments:
        params["promulgateEra"] = arguments["promulgateEra"]
    if "promulgateYear" in arguments:
        params["promulgateYear"] = arguments["promulgateYear"]
    if "category" in arguments:
        params["category"] = arguments["category"]
    if "offset" in arguments:
        params["offset"] = arguments["offset"]
    if "limit" in arguments:
        params["limit"] = arguments["limit"]
    else:
        params["limit"] = 100

    # 適切なURLエンコードを使用してクエリ文字列を構築
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/keyword?{query_string}"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    result = response.json()
    text = debug_info + json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


async def get_attachment(arguments: Dict[str, Any]) -> List[TextContent]:
    """添付ファイル取得 - /laws/{law_revision_id}/attachment エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_revision_id", "src"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_attachment で使用可能なパラメータ:\n"
            f"- law_revision_id: 法令履歴ID（必須）\n"
            f"- src: 添付ファイルのパス（必須）\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_revision_id" not in arguments:
        error_text = "エラー: law_revision_id パラメータは必須です"
        return [TextContent(type="text", text=error_text)]

    if "src" not in arguments:
        return [TextContent(type="text", text="エラー: src パラメータは必須です")]

    law_revision_id = arguments["law_revision_id"]
    src = arguments["src"]

    params = {"src": src}

    # 適切なURLエンコードを使用してクエリ文字列を構築
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/laws/{law_revision_id}/attachment?{query_string}"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    # バイナリデータの場合は、その旨を返却
    content_type = response.headers.get("content-type", "")
    if any(t in content_type for t in ["image", "pdf", "octet-stream"]):
        text = (
            debug_info + f"バイナリデータを取得しました。"
            f"コンテンツタイプ: {content_type}, "
            f"サイズ: {len(response.content)} bytes"
        )
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=debug_info + response.text)]


async def get_law_file(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令本文ファイル取得 - /laws/{law_revision_id}/lawfile エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_revision_id", "type"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_law_file で使用可能なパラメータ:\n"
            f"- law_revision_id: 法令履歴ID（必須）\n"
            f"- type: ファイルタイプ (pdf, docx, xml)（必須）\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_revision_id" not in arguments:
        error_text = "エラー: law_revision_id パラメータは必須です"
        return [TextContent(type="text", text=error_text)]

    if "type" not in arguments:
        return [TextContent(type="text", text="エラー: type パラメータは必須です")]

    law_revision_id = arguments["law_revision_id"]
    file_type = arguments["type"]

    params = {"type": file_type}

    # 適切なURLエンコードを使用してクエリ文字列を構築
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/laws/{law_revision_id}/lawfile?{query_string}"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    # ファイルデータの場合は、その旨を返却
    content_type = response.headers.get("content-type", "")
    if any(t in content_type for t in ["pdf", "docx", "octet-stream"]):
        text = (
            debug_info + f"ファイルデータを取得しました。"
            f"コンテンツタイプ: {content_type}, "
            f"サイズ: {len(response.content)} bytes"
        )
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=debug_info + response.text)]


async def main():
    """メイン関数"""
    try:
        # 標準入出力を使用してMCPプロトコルで通信
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            init_options = app.create_initialization_options()
            await app.run(read_stream, write_stream, init_options)
    except KeyboardInterrupt:
        pass
    finally:
        await http_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
