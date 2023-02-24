import json
import re
from copy import copy
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

from util import bcolors, DictNoNone

API_Object = Dict[str, str | bool | Dict[str, str]]


def get_note(parent, s: str):
    note: str = ''
    if s.endswith('*'):
        s, tag = s.split('*', 1)
        tag += '* '
        parent_content: List = parent["content"]
        for i in reversed(parent_content):
            if isinstance(i, str) and i.startswith(tag):
                note = i.removeprefix(tag)
                break
    return s.strip(), note


def parse_object_row(parent: Dict[str, Any], columns_in: Tuple[str], row_in: List[str]) -> API_Object:
    columns: List[str] = [c.title() for c in columns_in]
    row: List[str] = copy(row_in)

    comment: Dict[str, str] = DictNoNone()
    field_name: str = row.pop(0)
    columns.pop(0)
    field_type: str = row.pop(0)
    columns.pop(0)

    if 'Description' in columns:
        index = columns.index('Description')
        if index >= 0:
            comment["Description"], comment["Description Note"] = get_note(parent, row.pop(index))
            columns.pop(index)

    field_name, comment["Name Note"] = get_note(parent, field_name)
    field_type, comment["Type Note"] = get_note(parent, field_type)

    if len(columns):
        comment = {**comment, **dict(zip(columns, row))}

    optional: bool = field_name.endswith('?')
    field_name = field_name.removesuffix('?')
    nullable: bool = field_type.startswith('?')
    field_type = field_type.removeprefix('?')

    out = {
        'name': field_name,
        'type': field_type,
        'optional': optional,
        'nullable': nullable,
        'comments': comment
    }

    return out


ENUM_MATCH: List[Tuple[str]] = [
    ('action type', 'value'),
    ('event', 'value'),
    ('event type', 'value'),
    ('flag', 'value'),
    ('key', 'value'),
    ('level', 'integer'),
    ('level', 'value'),
    ('name', 'code'),
    ('preset type', 'value'),
    ('trigger type', 'value'),

    ('description', 'code'),

    ('name', 'id'),
    ('name', 'type'),
    ('name', 'value'),
    ('meaning', 'code'),
    ('mode', 'value'),
    ('permission', 'value'),
    ('type', 'id'),
    ('type', 'value'),
    ('feature',),
    ('features',),
    ('name',),
    ('status',),
    ('type',),
    ('value',)
]


def parse_enum_row(path: List[str], parent: Dict[str, Any], mapping: Tuple[str], columns_in: Tuple[str],
                   row_in: List[str]):
    columns: List[str] = [c.title() for c in columns_in]
    row: List[str] = copy(row_in)

    comments: Dict[str, str] = DictNoNone()

    name_index = columns.index(mapping[0].title())
    entry_name: str = row.pop(name_index)
    columns.pop(name_index)
    entry_value: str = ''
    if len(mapping) > 1:
        value_index = columns.index(mapping[1].title())
        entry_value = row.pop(value_index)
        columns.pop(value_index)

    entry_name, comments["Name Note"] = get_note(parent, entry_name)
    entry_value, comments["Value Note"] = get_note(parent, entry_value)

    for _ in range(len(columns)):
        column = columns.pop(0)
        comments[column], comments[f'{column} Note'] = get_note(parent, row.pop(0))

    out = {
        'name': entry_name
    }
    if entry_value:
        out['value'] = entry_value
    if comments:
        out['comments'] = comments

    return out


TABLE_MATCH: Dict[str, Set[str]] = {
    "object": {
        ('field', 'type'),
        ('field', 'type', 'associated action types', 'description'),
        ('field', 'type', 'associated trigger types', 'description'),
        ('field', 'type', 'description'),
        ('field', 'type', 'description', 'accepted values'),
        ('field', 'type', 'description', 'channel type'),
        ('field', 'type', 'description', 'default'),
        ('field', 'type', 'description', 'event types'),
        ('field', 'type', 'description', 'required'),
        ('field', 'type', 'description', 'permission'),
        ('field', 'type', 'description', 'present'),
        ('field', 'type', 'description', 'required', 'default'),
        ('field', 'type', 'description', 'required oauth2 scope'),
        ('field', 'type', 'description', 'valid types')
    },
    "enum": {
        ('action type', 'value', 'description'),
        ('code', 'description', 'explanation'),
        ('code', 'description', 'explanation', 'reconnect'),
        ('code', 'meaning'),
        ('code', 'name', 'client action', 'description'),
        ('code', 'name', 'description'),
        ('code', 'name', 'sent by', 'description'),
        ('event', 'value', 'description', 'object changed'),
        ('event type', 'value', 'description'),
        ('feature', 'description'),
        ('features', 'required permissions', 'effects'),
        ('flag', 'meaning', 'value'),
        ('flag', 'value', 'description'),
        ('flag', 'value', 'description', 'editable'),
        ('key', 'value', 'description'),
        ('level', 'integer', 'description'),
        ('level', 'value'),
        ('level', 'value', 'description'),
        ('id', 'name', 'format', 'example'),
        ('mode', 'value', 'description'),
        ('name', 'description'),
        ('name', 'type', 'description'),
        ('name', 'value'),
        ('name', 'value', 'color', 'required field'),
        ('name', 'value', 'description'),
        ('name', 'value', 'note'),
        ('status', 'description'),
        ('permission', 'value', 'description', 'channel type'),
        ('preset type', 'value', 'description'),
        ('trigger type', 'value', 'description', 'max per guild'),
        ('type', 'description'),
        ('type', 'id', 'description'),
        ('type', 'value'),
        ('type', 'value', 'deletable'),
        ('type', 'value', 'description'),
        ('type', 'value', 'description', 'max per guild'),
        ('value', 'description', 'example'),
        ('value', 'name'),
        ('value', 'name', 'description')
    },
    "ignored": {
        ('entity type', 'channel_id', 'entity_metadata', 'scheduled_end_time'),
        ('field', 'description', 'size'),
        ('field', 'limit'),
        ('field', 'type', 'size'),
        ('keyword', 'matches'),
        ('mode', 'key', 'nonce bytes', 'generating nonce'),
        ('name', 'language'),
        ('object changed', 'change key exceptions', 'change object exceptions'),
        ('permission', 'value', 'type', 'description'),
        ('field', 'trigger type', 'max array length', 'max characters per string'),
        ('type', 'format', 'image url'),
        ('type', 'name', 'description'),
        ('url', 'description'),
        ('version', 'out of service'),
        ('version', 'status', 'websocket url append')
    }
}

TABLE_NAME_IGNORE = {
    'HTTP Response Codes'
}


def extract(node: Dict[str, Any], path: List[str] = None):
    pretty_path: str = '->'.join(path) if path else 'Root'
    # print(pretty_path)

    if 'endpoint' in node:
        command, url = node['endpoint'].split(' ', 1)
        url = re.sub(r'#[^}]+}', '}', url)  # .replace('.', '_')
        url_params = {}
        for param in re.findall(r'(?<=\{)[^}]+(?=})', url):
            url_params[param] = {
                'type': 'snowflake' if param.endswith(".id") or param == "emoji" else 'string'
            }
        e = {
            'command': command,
            'url': url,
            'docs_url': node['url']
        }
        if url_params:
            e["url params"] = url_params
        endpoints[path[-1]] = e

    items = iter(node["content"])

    for item in items:
        match item:
            case str():
                s: str = item
                if s.startswith('|'):
                    header = s.removeprefix('|')
                    extract(node[header], (path or []) + [header])
                if s.startswith('*'):
                    # print(f'{pretty_path}\n{bcolors.OKCYAN}Unhandled note: {s}{bcolors.ENDC}')
                    pass
                else:
                    # print(f'{pretty_path}\n{bcolors.WARNING}Unknown string: {s}{bcolors.ENDC}')
                    pass
            case dict():
                d: dict = item
                if d.keys() == {'language', 'code'}:
                    # print(f'{pretty_path}\nIgnoring code block')
                    pass
                else:
                    print(f'{pretty_path}\n{bcolors.WARNING}Unknown dict: {item}{bcolors.ENDC}')
            case list():
                l: list = item
                match l[0]:
                    case list():
                        if path[-1] in TABLE_NAME_IGNORE:
                            continue

                        table: List[List[str]] = l

                        name = path[-1].removesuffix(' Structure').removesuffix(' Object').removesuffix(' Fields')
                        extra = re.search(r"\((.+)\)", name)
                        if extra:
                            extra = extra.groups()[0]
                            name = re.sub(r" \(.+\)", "", name)
                        if name == 'Payload' and path[0] == 'RPC':
                            name = 'RPC Payload'
                        elif name in ['JSON Response', 'Response Body', 'Response']:
                            name = path[-2] + ' Response'
                        elif name.endswith(' Params') and any(key in name for key in ['JSON', 'Form', 'Query String']):
                            if name == 'Gateway URL Query String Params':
                                continue
                            params_name = '|'
                            if extra:
                                params_name += f"{extra.lower()} "
                            params_name += next(iter(
                                key.lower()
                                for key in ['JSON/Form', 'JSON', 'Form', 'Query String']
                                if key in name
                            ))
                            name = params_name

                        columns = tuple(label.lower() for label in table[0])
                        match next((
                            match for match, matches in TABLE_MATCH.items()
                            if columns in matches
                        ), 'unmatched'):
                            case 'object':
                                # name = ''.join(name.title().split(' '))
                                # print(pretty_path)
                                # print(name)
                                o = dict()
                                for row in table[1:]:
                                    res = parse_object_row(node, tuple(table[0]), row)
                                    o[res.pop('name')] = res
                                if name.startswith('|'):
                                    endpoints[path[-2]][name[1:]] = o
                                elif name in objects.keys():
                                    objects[name] |= o
                                else:
                                    objects[name] = {
                                                        'parser-data': {
                                                            'docs_url': node['url']
                                                        }
                                                    } | o
                                # print()
                                pass
                            case 'enum':
                                # print(
                                #     f'{pretty_path}\n{bcolors.OKGREEN}'
                                #     f'enum: {str(columns)} {item[1:]}'
                                #     f'{bcolors.ENDC}'
                                # )
                                mapping = next((
                                    match for match in ENUM_MATCH
                                    if all(c in [c.lower() for c in table[0]] for c in match)
                                ), [])
                                e = dict()
                                for row in table[1:]:
                                    res = parse_enum_row(path, node, mapping, tuple(table[0]), row)
                                    e[res.pop('name')] = res
                                enums[name] = e
                            case 'ignored':
                                pass
                            case match:
                                print(
                                    f'{pretty_path}\n{bcolors.OKCYAN}'
                                    f'Unhandled {match} table: {str(columns)} {item[1:]}'
                                    f'{bcolors.ENDC}'
                                )
                    case str():
                        # print(f'{path} Ignoring string list')
                        pass
            case _:
                print(f'{pretty_path}\n{bcolors.WARNING}Unknown node: {item}{bcolors.ENDC}')
                pass


if __name__ == '__main__':
    for filepath in Path('./discord-api-json').rglob('*.json'):
        if '.' in filepath.stem \
                or len(filepath.parts) < 3 \
                or filepath.parts[1] in [
            'dispatch',
            'game_and_server_management',
            'game_sdk',
            'rich_presence',
            'tutorials'
        ] \
                or filepath.stem in [
            'Certified_Devices',
            'RPC'
        ]:
            # print(f'{bcolors.FAIL}{filepath.parts}{bcolors.ENDC}')
            continue
        # print(filepath.stem)
        # print(filepath.parts)
        objects: Dict[str, Dict[str, Any]] = {}
        enums: Dict[str, Dict[str, Any]] = {}
        endpoints: Dict[str, Dict[str, Any]] = {}
        extract(json.loads(filepath.read_bytes()))
        # target_dir = Path('./discord-api-json/', *filepath.parts[2:-1])
        # target_dir.mkdir(parents=True, exist_ok=True)
        if objects:
            path = filepath.parent.joinpath(f'{filepath.stem}.object.json')
            print("Writing to", path)
            path.write_text(json.dumps(objects, indent=2))
        if enums:
            path = filepath.parent.joinpath(f'{filepath.stem}.enum.json')
            print("Writing to", path)
            path.write_text(json.dumps(enums, indent=2))
        if endpoints:
            path = filepath.parent.joinpath(f'{filepath.stem}.endpoint.json')
            print("Writing to", path)
            path.write_text(json.dumps(endpoints, indent=2))
