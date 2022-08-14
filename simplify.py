import json
from copy import copy, deepcopy
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import List, Dict, Any

import mistletoe
from mistletoe.ast_renderer import ASTRenderer


# https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def flatten_content(node: Dict[str, Any], new_line: str = '', root: bool = True):
    out = new_line.removeprefix('\n') if root else ''
    children: List[Dict] = node["children"]
    for child in children:
        match child['type']:
            case 'LineBreak':
                out += new_line
            case _:
                out += child["content"] if "content" in child else flatten_content(child, new_line=new_line, root=False)
    return out


def traverse(target, path) -> dict:
    out = target
    for item in path:
        out = out.get(item)
    return out


def simplify(data) -> dict:
    md = json.loads(mistletoe.markdown(data, ASTRenderer))
    out = {"content": []}
    headers = []
    for node in md['children']:
        match node['type']:
            case 'Heading':
                level = node['level']
                content = node['children'][0]['content']
                headers = [*headers[:level], content]
                parent = traverse(out, headers[:-1])
                parent["content"].append('|' + content)
                parent[content] = {"content": []}
            case 'Table':
                traverse(out, headers)["content"].append([
                    [field['children'][0]['content'] for field in node['header']['children']],
                    *[[flatten_content(cell) for cell in row['children']] for row in node['children']]
                ])
            case 'Paragraph':
                traverse(out, headers)["content"].append(flatten_content(node, '\n'))
            case 'Quote':
                traverse(out, headers)["content"].append(flatten_content(node, '\n> '))
            case 'List':
                traverse(out, headers)["content"].append([flatten_content(item) for item in node['children']])
            case 'CodeFence':
                traverse(out, headers)["content"].append({
                    'language': node['language'],
                    'code': flatten_content(node, '\n')
                })
            case 'ThematicBreak':
                traverse(out, headers)["content"].append('―')
            case _:
                print(f'{bcolors.WARNING}Skipped a {node["type"]} at {headers}!{bcolors.ENDC}')
                print(node)
    return out


if __name__ == '__main__':
    for filepath in Path('./discord-api-docs/docs').rglob("*.md"):
        simplified = simplify(filepath.read_text(encoding='UTF-8'))
        # print(simplified)
        target_dir = Path('./discord-api-json/', *filepath.parts[2:-1])
        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir.joinpath(f'{filepath.stem}.json').write_text(json.dumps(simplified, indent=2))
