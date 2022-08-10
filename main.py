import json
from copy import copy, deepcopy
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any

import mistletoe
from mistletoe.ast_renderer import ASTRenderer


class HeaderType(Enum):
    NONE = 0
    OBJECT = 1
    ENUM = 2
    ENDPOINT = 3


def flatten_content(node: Dict[str, Any]):
    out = ""
    children: List[Dict] = node["children"]
    for child in children:
        out += child["content"] if "content" in child else flatten_content(child)
    return out


def parse_table(table) -> (List[str], List[Dict[str, str]]):
    columns = [field['children'][0]['content'].lower() for field in table['header']['children']]
    rows = []
    for row in table['children']:
        rows.append(dict(zip(columns, [flatten_content(cell) for cell in row['children']])))
    return columns, rows


def lower_keys(target: Dict[str, Any]):
    out = deepcopy(target)
    for key in out:
        if key.isupper():
            out[key.lower()] = out.pop(key)
    return target


def lower_items(target: List[str]):
    return [s.lower for s in target]


def parse_file(path):
    with Path(path).open(encoding='UTF-8') as file:
        md = json.loads(mistletoe.markdown(file, ASTRenderer))
        headers: List[str] = ['', '', '']
        header_type: HeaderType = HeaderType.NONE
        last_name = ""
        last_type: HeaderType.NONE
        objects = {}
        endpoints = {}
        enums = {}
        for node in md['children']:
            match node['type']:
                case 'Heading':
                    level = [0, 0, 1, 1, 2, 2, 2][node['level']]
                    content = node['children'][0]['content']
                    headers = [*headers[:level], content, *[''] * (2 - level)]
                    if headers[1].endswith('Object'):
                        if headers[2]:
                            if headers[2].endswith('Structure'):
                                header_type = HeaderType.OBJECT
                            else:
                                header_type = HeaderType.ENUM
                        else:
                            header_type = HeaderType.NONE
                    elif '%' in headers[1]:
                        header_type = HeaderType.ENDPOINT
                        if not headers[2]:
                            [name, _, command, url] = headers[1].rsplit(' ', 3)
                            while '#' in url:
                                index = url.find("#")
                                url = url[0: index] + url[str(url).find("}", index):]
                            endpoints[name] = {
                                "command": command,
                                "url": url
                            }
                            last_name = name
                case 'Table':
                    columns, rows = parse_table(node)
                    # print(headers)
                    # print(header_type)
                    # print(columns)
                    if header_type == HeaderType.OBJECT or (
                            header_type == HeaderType.ENDPOINT and (headers[2].endswith('Params'))
                    ):
                        name = headers[2].removesuffix(' Structure')
                        out = {}
                        for row in rows:
                            field: Dict[str, Any] = copy(row)
                            if 'name' in field:
                                field['field'] = field.pop('name')
                            if ' ' in field['field']:
                                [field['field'], field['note']] = field['field'].split(' ', 1)

                            if field['type'].endswith('*'):
                                [field['type'], field['note']] = field['type'].rsplit(' ', 1)

                            field['optional'] = field['field'].endswith('?')
                            field['field'] = field['field'].removesuffix('?')

                            field['nullable'] = field['type'].startswith('?')
                            field['type'] = field['type'].removeprefix('?')

                            out[field.pop("field")] = field
                        if header_type == HeaderType.OBJECT:
                            objects[name] = out
                            last_name = name
                        elif name == 'JSON Params':
                            # print(headers)
                            endpoints[last_name]['json'] = out
                        elif name == 'Query String Params':
                            # print(headers)
                            endpoints[last_name]['query'] = out
                    elif header_type == HeaderType.ENUM or header_type == HeaderType.ENDPOINT:
                        name = headers[2]
                        [_, enums[name]] = parse_table(node)
                        if header_type == HeaderType.ENUM:
                            last_name = name
                case 'Paragraph':
                    content = flatten_content(node)
                    # print(content)
                    if last_type == HeaderType.OBJECT and node['children'][0]['type'] == 'EscapeSequence':
                        marker, note = content.split(' ', 1)
                        for field in objects[last_name]:
                            if 'Note' in field and field['Note'] == marker:
                                field['Note'] = note

            last_type = type
    return objects, endpoints, enums


def run():
    for filepath in Path('./discord-api-docs/docs').rglob("*.md"):
        objects, endpoints, enums = parse_file(filepath)
        target = Path('./discord-api-json/', *filepath.parts[2:-1])
        if objects or endpoints or enums:
            target.mkdir(parents=True, exist_ok=True)
        if objects:
            target.joinpath(f'{filepath.stem}.object.json').write_text(json.dumps(objects, indent=2))
        if endpoints:
            target.joinpath(f'{filepath.stem}.endpoint.json').write_text(json.dumps(endpoints, indent=2))
        if enums:
            target.joinpath(f'{filepath.stem}.enum.json').write_text(json.dumps(enums, indent=2))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run()
