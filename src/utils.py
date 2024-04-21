import os
import json
import re
import xml.etree.ElementTree as ET


def take_json_text_from_triple_quotes(response: str):
    pattern = r'```[\s\t\n]*(\{.*?\})[\s\t\n]*```'
    match = re.search(pattern, response, re.DOTALL)
    result = match.group(1) if match else response
    return result


def fix_bad_json(s):
    i = 50
    result = None
    while i >= 0:
        i -= 1
        try:
            result = json.loads(s)  # try to parse...
            break  # parsing worked -> exit loop
        except Exception as e:
            # "Expecting , delimiter: line 34 column 54 (char 1158)"
            # position of unexpected character after '"'
            pos = int(re.findall(r'\(char (\d+)\)', str(e))[0])
            if s[pos] == '\\':
                s = f"{s[:pos]}\\{s[pos:]}"
            if s[pos] == '\n':
                s = f"{s[:pos]}\\n{s[pos:]}"
            else:
                print(f"Found bad character in json: at pos {pos}: '{s[pos]}': {s[pos-20:pos+20]}")
    return s


def parse_llm_response_to_json(response):
    print(response)
    response = response.strip().replace("```json", "```")
    response = re.sub(r"(?<!`)`(?!`)", "'", response)
    response = take_json_text_from_triple_quotes(response)
    response = fix_bad_json(response)
    response = json.loads(response)
    return response


def find_xml_structure(text):
    # Создаем регулярное выражение для поиска XML-структуры <root>...</root>
    pattern = r"<root>.*?<\/root>"
    # Используем re.search для поиска первого совпадения
    match = re.search(pattern, text, re.DOTALL)
    # Если совпадение найдено, возвращаем его
    if match:
        return match.group(0)
    # Если совпадений нет, возвращаем None
    return None


def parse_xml_llm_response(response):
    response = find_xml_structure(response)
    try:
        root = ET.fromstring(response)
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {}
    response_data = {}
    for child in root:
        response_data[child.tag] = child.text
    return response_data


def parse_xml_llm_response_commands(response):
    response = find_xml_structure(response)
    try:
        root = ET.fromstring(response)
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return {}
    commands = [cmd.text for cmd in root.findall('command')]
    return {"commands": commands}


def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
