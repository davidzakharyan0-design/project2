import json


def load_metadata(filepath):
    try:
        with open(filepath, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Метаданные должны быть JSON-объектом.")

    for table_name, columns in data.items():
        if not isinstance(columns, list):
            raise ValueError(f'Некорректная структура таблицы "{table_name}".')
        if not all(isinstance(column, str) for column in columns):
            raise ValueError(f'Некорректные столбцы таблицы "{table_name}".')

    return data


def save_metadata(filepath, data):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")
