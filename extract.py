import json
from copy import copy
from pathlib import Path
from typing import Dict, List, Callable, Tuple, Any

from util import bcolors, DictNoNone

API_Object = Dict[str, str | bool | Dict[str, str]]


def no_op(columns, row):
    return row


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


def parse_object_row(path: List[str], parent: Dict[str, Any], columns_in: Tuple[str], row_in: List[str]) -> API_Object:
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

    if path[-1].endswith('Params'):
        if 'Query String' in path[-1]:
            out['target'] = 'query string'
        elif 'JSON/Form' in path[-1]:
            out['target'] = 'json/form'
        elif 'JSON' in path[-1]:
            out['target'] = 'json'
        elif 'Form' in path[-1]:
            out['target'] = 'form'

    return out


TABLE_MATCH: Dict[
    str, Dict[
        Tuple[str], Callable[[List[str], Dict[str, Any], Tuple[str], List[str]], API_Object | Dict[str, str]]]] = {
    "object": {
        ('field', 'type'): parse_object_row,
        ('field', 'type', 'associated action types', 'description'): parse_object_row,
        ('field', 'type', 'associated trigger types', 'description'): parse_object_row,
        ('field', 'type', 'description'): parse_object_row,
        ('field', 'type', 'description', 'accepted values'): parse_object_row,
        ('field', 'type', 'description', 'channel type'): parse_object_row,
        ('field', 'type', 'description', 'default'): parse_object_row,
        ('field', 'type', 'description', 'event types'): parse_object_row,
        ('field', 'type', 'description', 'required'): parse_object_row,
        ('field', 'type', 'description', 'permission'): parse_object_row,
        ('field', 'type', 'description', 'present'): parse_object_row,
        ('field', 'type', 'description', 'required', 'default'): parse_object_row,
        ('field', 'type', 'description', 'required oauth2 scope'): parse_object_row,
        ('field', 'type', 'description', 'valid types'): parse_object_row
    },
    "enum": {
        ('code', 'name', 'client action', 'description'): no_op,
        ('code', 'description', 'explanation'): no_op,
        ('code', 'description', 'explanation', 'reconnect'): no_op,
        ('code', 'meaning'): no_op,
        ('code', 'name', 'description'): no_op,
        ('code', 'name', 'sent by', 'description'): no_op,
        ('event', 'value', 'description', 'object changed'): no_op,
        ('feature', 'description'): no_op,
        ('field', 'description'): no_op,
        ('flag', 'meaning', 'value'): no_op,
        ('flag', 'value', 'description'): no_op,
        ('key', 'value', 'description'): no_op,
        ('level', 'value'): no_op,
        ('level', 'value', 'description'): no_op,
        ('level', 'integer', 'description'): no_op,
        ('id', 'name', 'format', 'example'): no_op,
        ('mode', 'value', 'description'): no_op,
        ('name', 'description'): no_op,
        ('name', 'type', 'description'): no_op,
        ('name', 'value'): no_op,
        ('name', 'value', 'color', 'required field'): no_op,
        ('name', 'value', 'description'): no_op,
        ('name', 'value', 'note'): no_op,
        ('status', 'description'): no_op,
        ('permission', 'value', 'description', 'channel type'): no_op,
        ('type', 'description'): no_op,
        ('type', 'id'): no_op,
        ('type', 'id', 'description'): no_op,
        ('type', 'value'): no_op,
        ('type', 'value', 'description'): no_op,
        ('type', 'value', 'description', 'max per guild'): no_op,
        ('value', 'description', 'example'): no_op,
        ('value', 'name'): no_op,
        ('value', 'name', 'description'): no_op
    },
    "ignored": {
        ('entity type', 'channel_id', 'entity_metadata', 'scheduled_end_time'): no_op,
        ('field', 'description', 'size'): no_op,
        ('field', 'limit'): no_op,
        ('field', 'type', 'size'): no_op,
        ('keyword', 'matches'): no_op,
        ('mode', 'key', 'nonce bytes', 'generating nonce'): no_op,
        ('name', 'language'): no_op,
        ('object changed', 'change key exceptions', 'change object exceptions'): no_op,
        ('permission', 'value', 'type', 'description'): no_op,
        ('type', 'format', 'image url'): no_op,
        ('type', 'name', 'description'): no_op,
        ('url', 'description'): no_op,
        ('version', 'out of service'): no_op,
        ('version', 'status', 'websocket url append'): no_op
    },
    "no match": {}
}

names = set()


def extract(docs: Dict[str, Dict[str, Any]], path: List[str] = None):
    pretty_path: str = '->'.join(path) if path else 'Root'
    # print(pretty_path)

    for item in docs["content"]:
        match item:
            case str():
                s: str = item
                if s.startswith('|'):
                    header = s.removeprefix('|')
                    extract(docs[header], (path or []) + [header])
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
                        table: List[List[str]] = l

                        name = path[-1].removesuffix(' Structure').removesuffix(' Object').removesuffix(' Fields')
                        if name == 'Payload' and path[0] == 'RPC':
                            name = 'RPC Payload'
                        elif name in ['JSON Response', 'Response Body', 'Response']:
                            name = path[-2] + ' Response'
                        elif name.endswith(' Params') and any(key in name for key in ['JSON', 'Form', 'Query String']):
                            name = path[-2] + ' Params'

                        columns = tuple(label.lower() for label in table[0])
                        match: str = ''
                        matches: Dict[Tuple[str], Callable[
                            [List[str], Dict[str, Any], Tuple[str], List[str]], API_Object | Dict[str, str]]] = {}
                        for match, matches in TABLE_MATCH.items():
                            if columns in matches:
                                break
                        match match:
                            case 'object':
                                name = ''.join(name.title().split(' '))
                                print(pretty_path)
                                print(name)
                                o = dict()
                                for row in table[1:]:
                                    res = matches[columns](path, docs, tuple(table[0]), row)
                                    o[res.pop('name')] = res
                                names.add(name)
                                if name in objects.keys():
                                    objects[name] |= o
                                else:
                                    objects[name] = {
                                                        "parser-data": {
                                                            "docs_url": docs["url"]
                                                        }
                                                    } | o
                                print()
                                pass
                            case 'enum':
                                pass
                            case 'ignored':
                                pass
                            case 'no match':
                                print(
                                    f'{pretty_path}\n{bcolors.WARNING}'
                                    f'Unknown table: {str(columns)}: no_op, {item[1:]}'
                                    f'{bcolors.ENDC}'
                                )
                                print(docs["url"])
                            case _:
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
    for filepath in Path('./discord-api-json').rglob("*.json"):
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
        print(filepath.stem)
        # print(filepath.parts)
        objects: Dict[str, Dict[str, Any]] = {}
        extract(json.loads(filepath.read_bytes()))
        # target_dir = Path('./discord-api-json/', *filepath.parts[2:-1])
        # target_dir.mkdir(parents=True, exist_ok=True)
        if objects:
            filepath.parent.joinpath(f'{filepath.stem}.object.json').write_text(json.dumps(objects, indent=2))
