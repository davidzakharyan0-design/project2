import shlex

import prompt

from primitive_db.core import create_table, drop_table, list_tables
from primitive_db.utils import load_metadata, save_metadata

METADATA_FILE = "db_meta.json"


def print_help():
    print("\n***База данных***")
    print("\nФункции:")
    print(
        "<command> create_table <имя_таблицы> <столбец1:тип> "
        "<столбец2:тип> ... — создать таблицу"
    )
    print("<command> list_tables — показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> — удалить таблицу")
    print("<command> exit — выйти из программы")
    print("<command> help — справочная информация")
    print("\nТипы данных: int, str, bool.\n")


def check_arguments(arguments, minimum, maximum=None):
    if len(arguments) < minimum:
        raise ValueError(
            "Некорректное значение: недостаточно аргументов. "
            "Введите help для справки. Попробуйте снова."
        )

    if maximum is not None and len(arguments) > maximum:
        raise ValueError("Некорректное значение: лишние аргументы. Попробуйте снова.")


def run():
    print_help()

    while True:
        try:
            metadata = load_metadata(METADATA_FILE)
        except (OSError, ValueError) as error:
            print(f"Ошибка чтения метаданных: {error}")
            return

        try:
            user_input = prompt.string("Введите команду: ")
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            return

        try:
            parts = shlex.split(user_input)
        except ValueError:
            print(
                f"Некорректное значение: {user_input}. "
                "Проверьте кавычки. Попробуйте снова."
            )
            continue

        if not parts:
            continue

        command = parts[0]
        arguments = parts[1:]

        try:
            if command == "exit":
                check_arguments(arguments, 0, 0)
                print("До свидания!")
                break

            elif command == "help":
                check_arguments(arguments, 0, 0)
                print_help()

            elif command == "list_tables":
                check_arguments(arguments, 0, 0)
                tables = list_tables(metadata)

                if not tables:
                    print("Таблиц пока нет.")

                for table_name in tables:
                    print(f"- {table_name}")

            elif command == "create_table":
                check_arguments(arguments, 2)
                table_name = arguments[0]
                columns = arguments[1:]

                metadata = create_table(metadata, table_name, columns)
                save_metadata(METADATA_FILE, metadata)

                description = ", ".join(metadata[table_name])
                print(
                    f'Таблица "{table_name}" успешно создана '
                    f"со столбцами: {description}"
                )

            elif command == "drop_table":
                check_arguments(arguments, 1, 1)
                table_name = arguments[0]

                metadata = drop_table(metadata, table_name)
                save_metadata(METADATA_FILE, metadata)

                print(f'Таблица "{table_name}" успешно удалена.')

            else:
                print(f"Функции {command} нет. Попробуйте снова.")

        except ValueError as error:
            print(error)
        except OSError as error:
            print(f"Ошибка сохранения метаданных: {error}")
