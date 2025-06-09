#!/usr/bin/env python3
import asyncio
import json
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent


app = Server("egov-mcp")
BASE_URL = "https://laws.e-gov.go.jp/api/2"
http_client = httpx.AsyncClient(timeout=30.0)


def extract_fields(data: Any, fields: List[str]) -> Any:
    """JSONデータから指定されたフィールドのみを抽出する"""
    if not fields:
        return data
    
    if isinstance(data, dict):
        result = {}
        # ネストフィールドをキーごとにグループ化
        nested_fields = {}
        direct_fields = []
        
        for field in fields:
            if "." in field:
                # ネストされたフィールド（例：law_info.law_title）
                parts = field.split(".", 1)
                key, nested_field = parts[0], parts[1]
                if key not in nested_fields:
                    nested_fields[key] = []
                nested_fields[key].append(nested_field)
            else:
                # 直接フィールド
                direct_fields.append(field)
        
        # 直接フィールドを処理
        for field in direct_fields:
            if field in data:
                result[field] = data[field]
        
        # ネストフィールドをキーごとにまとめて処理
        for key, nested_field_list in nested_fields.items():
            if key in data:
                nested_result = extract_fields(data[key], nested_field_list)
                # 辞書の場合は空でない場合のみ追加、リストの場合は常に追加
                if isinstance(nested_result, dict):
                    if nested_result:  # 空辞書でない場合のみ追加
                        result[key] = nested_result
                else:
                    result[key] = nested_result  # リストやその他の型は常に追加
                    
        return result
    elif isinstance(data, list):
        return [extract_fields(item, fields) for item in data]
    else:
        return data


def get_content_type_fields(
    content_type: str, api_type: str = "law_data"
) -> List[str]:
    """content_typeとAPI種別に基づいて取得するフィールドを決定する"""
    
    if api_type == "law_data":
        # 法令本文取得API用のフィールド
        if content_type == "title_only":
            return [
                "law_info.law_type", "law_info.law_num", 
                "revision_info.law_title", "revision_info.law_title_kana"
            ]
        elif content_type == "body_only":
            return ["law_full_text"]
        elif content_type == "summary":
            # 改善された要約モード - より詳細な情報を含む
            return [
                "law_info", "revision_info.law_title", 
                "revision_info.category",
                "revision_info.amendment_enforcement_date", 
                "revision_info.current_revision_status",
                "revision_info.law_revision_id",
                "law_full_text"
            ]
        elif content_type == "basic_info":
            return [
                "law_info", "revision_info.law_title", 
                "revision_info.law_title_kana",
                "revision_info.category", "revision_info.updated"
            ]
    
    elif api_type == "laws":
        # 法令一覧取得API用のフィールド
        if content_type == "title_only":
            return [
                "total_count", "count",
                "laws.law_info.law_type", "laws.law_info.law_num",
                "laws.revision_info.law_title", 
                "laws.revision_info.law_title_kana"
            ]
        elif content_type == "summary":
            return [
                "total_count",
                "count",
                "laws.law_info.law_type",
                "laws.law_info.law_num",
                "laws.law_info.promulgation_date",
                "laws.revision_info.law_title",
                "laws.revision_info.category",
                "laws.revision_info.law_revision_id",
                "laws.revision_info.current_revision_status",
                "laws.revision_info.amendment_enforcement_date"
            ]
        elif content_type == "basic_info":
            return [
                "total_count", "count", "laws.law_info", 
                "laws.revision_info.law_title",
                "laws.revision_info.category"
            ]
    
    elif api_type == "revisions":
        # 法令履歴一覧取得API用のフィールド
        if content_type == "title_only":
            return [
                "law_info.law_type", "law_info.law_num",
                "revisions.law_title", "revisions.law_title_kana"
            ]
        elif content_type == "summary":
            return [
                "law_info", "revisions.law_title", "revisions.category",
                "revisions.amendment_enforcement_date", 
                "revisions.current_revision_status"
            ]
        elif content_type == "basic_info":
            return [
                "law_info", "revisions.law_title", "revisions.updated"
            ]
    
    elif api_type == "keyword_search":
        # キーワード検索API用のフィールド
        if content_type == "title_only":
            return [
                "total_count", "sentence_count",
                "items.law_info.law_type", "items.law_info.law_num",
                "items.revision_info.law_title", 
                "items.revision_info.law_title_kana"
            ]
        elif content_type == "summary":
            return [
                "total_count", "sentence_count", "next_offset",
                "items.law_info", "items.revision_info.law_title", 
                "items.revision_info.category", "items.sentences"
            ]
        elif content_type == "basic_info":
            return [
                "total_count", "sentence_count",
                "items.law_info", "items.revision_info.law_title"
            ]
    
    # "full" または不明なcontent_typeの場合は全フィールドを返す
        return []


def filter_current_laws(data: Any) -> Any:
    """現行法令のみをフィルタリングする"""
    if isinstance(data, dict):
        if "laws" in data and isinstance(data["laws"], list):
            # 法令一覧の場合
            filtered_laws = [
                law for law in data["laws"]
                if law.get("revision_info", {}).get(
                    "current_revision_status"
                ) == "CurrentEnforced"
            ]
            result = data.copy()
            result["laws"] = filtered_laws
            result["count"] = len(filtered_laws)
            return result
        elif "revisions" in data and isinstance(data["revisions"], list):
            # 履歴一覧の場合
            filtered_revisions = [
                revision for revision in data["revisions"]
                if revision.get("current_revision_status") == "CurrentEnforced"
            ]
            result = data.copy()
            result["revisions"] = filtered_revisions
            return result
    return data


def format_response(
    result: Any, 
    debug_info: str, 
    fields_only: Optional[List[str]] = None,
    filter_current: bool = False
) -> str:
    """レスポンスをフォーマットする"""
    processed_result = result
    
    if filter_current:
        processed_result = filter_current_laws(result)
    
    if fields_only:
        filtered_result = extract_fields(processed_result, fields_only)
        return debug_info + json.dumps(
            filtered_result, ensure_ascii=False, indent=2
        )
    else:
        return debug_info + json.dumps(
            processed_result, ensure_ascii=False, indent=2
        )


@app.list_tools()
async def list_tools() -> List[Tool]:
    """利用可能なツールのリストを返す"""
    law_types = [
        "Constitution", "Act", "CabinetOrder", 
        "MinisterialOrdinance", "Rule"
    ]
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
                    "law_num_year": {
                        "type": "integer", 
                        "description": "法令番号の年"
                    },
                    "category": {
                        "type": "string", 
                        "description": "法令カテゴリ"
                    },
                    "promulgation_date": {
                        "type": "string",
                        "description": "公布日（YYYY-MM-DD形式）",
                    },
                    "content_type": {
                        "type": "string",
                        "enum": [
                            "full", "title_only", "summary", "basic_info"
                        ],
                        "description": (
                            "取得する内容タイプ：\n"
                            "- full: 全情報（デフォルト）\n"
                            "- title_only: タイトル関連のみ\n"
                            "- summary: サマリー情報\n"
                            "- basic_info: 基本情報のみ"
                        ),
                        "default": "full",
                    },
                    "response_format": {
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
                    "fields_only": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "取得したいフィールドのみを指定"
                            "（例：['laws.law_title', 'laws.law_id']）"
                        ),
                    },
                    "filter_current_only": {
                        "type": "boolean",
                        "description": "現行法令のみを取得するかどうか",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_law_data",
            description="特定の法令の本文データを取得します（法令ID/番号/履歴IDを指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_revision_id": {
                        "type": "string", 
                        "description": "法令ID/番号/履歴ID"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": [
                            "full", "title_only", "body_only", 
                            "summary", "basic_info"
                        ],
                        "description": (
                            "取得する内容タイプ：\n"
                            "- full: 全情報（デフォルト）\n"
                            "- title_only: タイトル関連のみ\n"
                            "- body_only: 本文のみ\n"
                            "- summary: サマリー情報（タイトル、公布日、施行日など）\n"
                            "- basic_info: 基本情報（メタデータのみ）"
                        ),
                        "default": "full",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["json", "xml"],
                        "description": "取得フォーマット（デフォルト: json）",
                        "default": "json",
                    },
                    "fields_only": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "取得したいフィールドのみを指定（content_typeより優先）",
                    },
                },
                "required": ["law_revision_id"],
            },
        ),
        Tool(
            name="get_law_revisions",
            description="特定の法令の履歴一覧を取得します（法令IDまたは法令番号を指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_id": {
                        "type": "string", 
                        "description": "法令IDまたは法令番号"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": [
                            "full", "title_only", "summary", "basic_info"
                        ],
                        "description": (
                            "取得する内容タイプ：\n"
                            "- full: 全情報（デフォルト）\n"
                            "- title_only: タイトル関連のみ\n"
                            "- summary: サマリー情報\n"
                            "- basic_info: 基本情報のみ"
                        ),
                        "default": "full",
                    },
                    "fields_only": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "取得したいフィールドのみを指定",
                    },
                },
                "required": ["law_id"],
            },
        ),
        Tool(
            name="search_keyword",
            description="法令本文内のキーワード検索を行います",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string", 
                        "description": "検索キーワード"
                    },
                    "law_type": {
                        "type": "string",
                        "enum": law_types,
                        "description": "法令種別",
                    },
                    "promulgate_era": {
                        "type": "string",
                        "enum": eras,
                        "description": "公布年代",
                    },
                    "promulgate_year": {
                        "type": "integer", 
                        "description": "公布年"
                    },
                    "category": {
                        "type": "string", 
                        "description": "法令分類"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": [
                            "full", "title_only", "summary", "basic_info"
                        ],
                        "description": (
                            "取得する内容タイプ：\n"
                            "- full: 全情報（デフォルト）\n"
                            "- title_only: タイトル関連のみ\n"
                            "- summary: サマリー情報\n"
                            "- basic_info: 基本情報のみ"
                        ),
                        "default": "full",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["json", "xml"],
                        "description": "取得フォーマット（デフォルト: json）",
                        "default": "json",
                    },
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
                    "fields_only": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "取得したいフィールドのみを指定",
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
                    "law_revision_id": {
                        "type": "string", 
                        "description": "法令履歴ID"
                    },
                    "src": {
                        "type": "string", 
                        "description": "添付ファイルのパス"
                    },
                },
                "required": ["law_revision_id", "src"],
            },
        ),
        Tool(
            name="get_law_file",
            description="法令本文ファイルを取得します（法令ID/番号/履歴IDとファイル形式を指定）",
            inputSchema={
                "type": "object",
                "properties": {
                    "law_revision_id": {
                        "type": "string", 
                        "description": "法令ID/番号/履歴ID"
                    },
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
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return [TextContent(type="text", text=(
                f"Error: リクエストしたリソースが見つかりません。\n"
                f"詳細: {str(e)}\n"
                f"リクエストURL: {e.request.url}\n\n"
                f"対処法:\n"
                f"- 法令IDや履歴IDが正しいかご確認ください\n"
                f"- 法令名での検索は get_laws を使用してください\n"
                f"- キーワード検索は search_keyword を使用してください"
            ))]
        else:
            return [TextContent(type="text", text=(
                f"HTTP Error {e.response.status_code}: {str(e)}\n"
                f"リクエストURL: {e.request.url}"
            ))]
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
        "content_type",
        "response_format",
        "limit",
        "fields_only",
        "filter_current_only",
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
            f"- response_format: 取得フォーマット (json, xml)（デフォルト: json）\n"
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
    if "law_num_era" in arguments:
        params["law_num_era"] = arguments["law_num_era"]
    if "law_num_year" in arguments:
        params["law_num_year"] = arguments["law_num_year"]

    # その他のパラメータ設定
    if "law_type" in arguments:
        params["law_type"] = arguments["law_type"]
    if "category" in arguments:
        params["category"] = arguments["category"]
    if "promulgation_date" in arguments:
        params["promulgation_date"] = arguments["promulgation_date"]
    if "response_format" in arguments:
        params["response_format"] = arguments["response_format"]
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
    
    # content_typeとfields_onlyの処理
    content_type = arguments.get("content_type", "full")
    fields_to_extract = arguments.get("fields_only")
    if not fields_to_extract and content_type != "full":
        fields_to_extract = get_content_type_fields(content_type, "laws")
    
    # 現行法令フィルタリングの処理
    filter_current = arguments.get("filter_current_only", False)
    
    text = format_response(
        result, debug_info, fields_to_extract, filter_current
    )
    return [TextContent(type="text", text=text)]


async def get_law_data(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令本文取得 - /law_data/{law_id_or_num_or_revision_id} エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {
        "law_revision_id", "content_type", "response_format", "fields_only"
    }

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: "
            f"{', '.join(invalid_params)}\n\n"
            f"get_law_data で使用可能なパラメータ:\n"
            f"- law_revision_id: 法令ID/番号/履歴ID（必須）\n"
            f"- content_type: 取得する内容タイプ (full, title_only, "
            f"body_only, summary, basic_info)\n"
            f"- response_format: 取得フォーマット (json, xml)"
            f"（デフォルト: json）\n"
            f"- fields_only: 取得したいフィールドのみを指定\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_revision_id" not in arguments:
        return [
            TextContent(
                type="text", text="エラー: law_revision_id パラメータは必須です"
            )
        ]

    law_revision_id = arguments["law_revision_id"]
    content_type = arguments.get("content_type", "full")
    format_type = arguments.get("response_format", "json")

    params = {"response_format": format_type}

    # 適切なURLエンコードを使用してクエリ文字列を構築
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/law_data/{law_revision_id}?{query_string}"

    response = await http_client.get(url)
    response.raise_for_status()

    debug_info = f"Request URL: {url}\n"

    if format_type == "json":
        result = response.json()
        
        # fields_onlyが指定されている場合はそれを優先、
        # そうでなければcontent_typeに基づいてフィールドを決定
        fields_to_extract = arguments.get("fields_only")
        if not fields_to_extract and content_type != "full":
            fields_to_extract = get_content_type_fields(
                content_type, "law_data"
            )
        
        text = format_response(result, debug_info, fields_to_extract)
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=debug_info + response.text)]


async def get_law_revisions(arguments: Dict[str, Any]) -> List[TextContent]:
    """法令履歴一覧取得 - /law_revisions/{law_id_or_num} エンドポイント用"""
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_id", "content_type", "fields_only"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_law_revisions で使用可能なパラメータ:\n"
            f"- law_id: 法令IDまたは法令番号（必須）\n"
            f"- content_type: 取得する内容タイプ (full, title_only, "
            f"summary, basic_info)\n"
        )
        return [TextContent(type="text", text=error_msg)]

    if "law_id" not in arguments:
        return [TextContent(type="text", text="エラー: law_id パラメータは必須です")]

    law_id = arguments["law_id"]

    url = f"{BASE_URL}/law_revisions/{law_id}"
    debug_info = f"Request URL: {url}\n"

    response = await http_client.get(url)
    response.raise_for_status()

    result = response.json()
    
    # content_typeとfields_onlyの処理
    content_type = arguments.get("content_type", "full")
    fields_to_extract = arguments.get("fields_only")
    if not fields_to_extract and content_type != "full":
        fields_to_extract = get_content_type_fields(content_type, "revisions")
    
    text = format_response(result, debug_info, fields_to_extract)
    return [TextContent(type="text", text=text)]


async def search_keyword(arguments: Dict[str, Any]) -> List[TextContent]:
    """キーワード検索 - /keyword エンドポイント用"""
    # 有効なパラメータのリスト
    valid_params = {
        "keyword",
        "law_type",
        "promulgate_era",
        "promulgate_year",
        "category",
        "content_type",
        "response_format",
        "offset",
        "limit",
        "fields_only",
    }

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"search_keyword で使用可能なパラメータ:\n"
            f"- keyword: 検索キーワード（必須）\n"
            f"- law_type: 法令種別 (Constitution, Act, CabinetOrder, "
            f"MinisterialOrdinance, Rule)\n"
            f"- promulgate_era: 公布年代 (Meiji, Taisho, Showa, "
            f"Heisei, Reiwa)\n"
            f"- promulgate_year: 公布年\n"
            f"- category: 法令分類\n"
            f"- content_type: 取得する内容タイプ (full, title_only, "
            f"summary, basic_info)\n"
            f"- response_format: 取得フォーマット (json, xml)（デフォルト: json）\n"
            f"- offset: 取得開始位置（デフォルト: 0）\n"
            f"- limit: 取得数（デフォルト: 100、最大: 500）\n\n"
            f"※法令名で検索する場合は get_laws を使用してください。"
        )
        return [TextContent(type="text", text=error_msg)]

    if "keyword" not in arguments:
        return [TextContent(type="text", text="エラー: keyword パラメータは必須です")]

    params = {"keyword": arguments["keyword"]}

    # キーワード検索APIで有効なパラメータのみ設定
    if "law_type" in arguments:
        params["law_type"] = arguments["law_type"]
    if "promulgate_era" in arguments:
        params["promulgate_era"] = arguments["promulgate_era"]
    if "promulgate_year" in arguments:
        params["promulgate_year"] = arguments["promulgate_year"]
    if "category" in arguments:
        params["category"] = arguments["category"]
    if "content_type" in arguments:
        params["content_type"] = arguments["content_type"]
    if "response_format" in arguments:
        params["response_format"] = arguments["response_format"]
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

    format_type = arguments.get("response_format", "json")
    
    if format_type == "json":
        result = response.json()
        
        # content_typeとfields_onlyの処理
        content_type = arguments.get("content_type", "full")
        fields_to_extract = arguments.get("fields_only")
        if not fields_to_extract and content_type != "full":
            fields_to_extract = get_content_type_fields(
                content_type, "keyword_search"
            )
        
        text = format_response(result, debug_info, fields_to_extract)
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=debug_info + response.text)]


async def get_attachment(arguments: Dict[str, Any]) -> List[TextContent]:
    """添付ファイル取得 - /attachment/{law_revision_id} エンドポイント用"""
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
    url = f"{BASE_URL}/attachment/{law_revision_id}?{query_string}"

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
    """
    法令本文ファイル取得 - /law_file/{file_type}/{law_id_or_num_or_revision_id}
    エンドポイント用
    """
    # バリデーション: 有効なパラメータのリスト
    valid_params = {"law_revision_id", "type"}

    # 無効なパラメータをチェック
    invalid_params = set(arguments.keys()) - valid_params
    if invalid_params:
        error_msg = (
            f"エラー: 無効なパラメータが検出されました: {', '.join(invalid_params)}\n\n"
            f"get_law_file で使用可能なパラメータ:\n"
            f"- law_revision_id: 法令ID/番号/履歴ID（必須）\n"
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

    # 新しいエンドポイント形式: /law_file/{file_type}/{law_id_or_num_or_revision_id}
    url = f"{BASE_URL}/law_file/{file_type}/{law_revision_id}"

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
