import json
from pathlib import Path
from typing import List, Dict, Any

import mistletoe
from mistletoe.ast_renderer import ASTRenderer

from util import traverse, bcolors


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


def simplify(filepath) -> dict:
    md = json.loads(mistletoe.markdown(filepath.read_text(encoding='UTF-8'), ASTRenderer))
    out = {"content": []}
    headers = ['' for _ in range(6)]
    for node in md['children']:
        match node['type']:
            case 'Heading':
                level = node['level']
                content = node['children'][0]['content']
                headers = [*headers[:level], content, *['' for _ in range(6 - level)]]
                parent = traverse(out, headers[:level])
                parent["content"].append('|' + content)
                url: str = f'https://discord.com/developers/docs/{filepath.parts[-2]}/' \
                           f'{filepath.stem.lower().replace("_", "-")}#'
                if level <= 3:
                    url += headers[level].lower().replace(" ", "-")
                else:
                    url += "-".join([h.lower().replace(" ", "-") for h in [headers[parent["level"]], headers[level]]])
                parent[content] = {
                    "level": level,
                    "url": url,
                    "content": []
                }
            case 'Table':
                traverse(out, headers)["content"].append([
                    [field['children'][0]['content'] for field in node['header']['children']],
                    *[[flatten_content(cell) for cell in row['children']] for row in node['children']]
                ])
                pass
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
        simplified = simplify(filepath)
        # print(simplified)
        target_dir = Path('./discord-api-json/', *filepath.parts[2:-1])
        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir.joinpath(f'{filepath.stem}.json').write_text(json.dumps(simplified, indent=2))
