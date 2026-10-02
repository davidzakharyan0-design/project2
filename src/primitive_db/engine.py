import prompt
from prettytable import PrettyTable

from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    get_schema,
    insert,
    list_tables,
    select,
    update,
    validate_fields,
    validate_table_data,
)
from primitive_db.decorators import CANCELLED, DB_ERROR, handle_db_errors
from primitive_db.parser import parse_command
from primitive_db.utils import (
    delete_table_data,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)

METADATA_FILE = "db_meta.json"


def print_help():
    print("\n***База данных: таблицы и операции с данными***\n")
    print("create_table <таблица> <столбец:тип> ... — создать таблицу")
    print("list_tables — показать таблицы")
    print("drop_table <таблица> — удалить таблицу и её данные")
    print("insert into <таблица> values (<значение>, ...) — добавить запись")
    print("select from <таблица> [where <столбец> = <значение>] — прочитать записи")
    print(
        "update <таблица> set <столбец> = <значение> "
        "where <столбец> = <значение> — обновить записи"
    )
    print("delete from <таблица> where <столбец> = <значение> — удалить записи")
    print("info <таблица> — информация о таблице")
    print("help — справка; exit — выход")
    print('Типы: int, str, bool. Строки в кавычках: "Sergei"; bool: true/false.')
    print("ID генерируется автоматически. Удаление требует подтверждения y.\n")


def print_rows(schema, rows):
    table = PrettyTable()
    table.field_names = list(schema)
    for row in rows:
        table.add_row([row[name] for name in schema])
    print(table)
    if not rows:
        print("Записи не найдены.")


@handle_db_errors
def execute(metadata, parsed):
    command, table_name, values, condition = parsed
    if command == "help":
        print_help()
        return
    if command == "list_tables":
        tables = list_tables(metadata)
        print("\n".join(f"- {name}" for name in tables) or "Таблиц пока нет.")
        return
    if command == "create_table":
        changed = create_table(dict(metadata), table_name, values)
        save_table_data(table_name, [])
        save_metadata(METADATA_FILE, changed)
        columns = ", ".join(changed[table_name])
        print(f'Таблица "{table_name}" успешно создана со столбцами: {columns}')
        return
    if command == "drop_table":
        get_schema(metadata, table_name)
        changed = drop_table(dict(metadata), table_name)
        if changed is CANCELLED:
            return CANCELLED
        delete_table_data(table_name)
        save_metadata(METADATA_FILE, changed)
        print(f'Таблица "{table_name}" успешно удалена.')
        return

    schema = get_schema(metadata, table_name)
    table_data = load_table_data(table_name)
    validate_table_data(schema, table_data)
    if condition is not None:
        validate_fields(schema, condition)

    if command == "insert":
        changed = insert(metadata, table_name, values)
        save_table_data(table_name, changed)
        print(f'Запись с ID={changed[-1]["ID"]} добавлена в таблицу "{table_name}".')
    elif command == "select":
        print_rows(schema, select(table_data, condition))
    elif command == "info":
        print(f"Таблица: {table_name}")
        print(f"Столбцы: {', '.join(metadata[table_name])}")
        print(f"Количество записей: {len(table_data)}")
    elif command in {"update", "delete"}:
        if command == "update":
            validate_fields(schema, values, allow_id=False)
        affected = select(table_data, condition)
        if not affected:
            print("Записи не найдены.")
            return
        if command == "update":
            changed = update(table_data, values, condition)
            action = "обновлена"
        else:
            changed = delete(table_data, condition)
            action = "удалена"
        if changed is CANCELLED:
            return CANCELLED
        save_table_data(table_name, changed)
        for row in affected:
            print(f"Запись с ID={row['ID']}: успешно {action} ({table_name}).")


@handle_db_errors
def process_command(metadata, user_input):
    parsed = parse_command(user_input)
    if parsed is None:
        return None
    if parsed[0] == "exit":
        return "exit"
    return execute(metadata, parsed)


@handle_db_errors
def read_metadata():
    return load_metadata(METADATA_FILE)


def run():
    print_help()
    while True:
        metadata = read_metadata()
        if metadata is DB_ERROR:
            return
        try:
            user_input = prompt.string("Введите команду: ")
            result = process_command(metadata, user_input)
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return
        if result == "exit":
            print("До свидания!")
            return
