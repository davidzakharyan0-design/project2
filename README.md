# Primitive DB

Учебное консольное приложение для работы с простой базой данных.

Требования: Python 3.12 и установленный uv.

## Установка и запуск

```bash
uv sync
uv run project
```

## Запуск как модуля

```bash
uv run python -m primitive_db.main
```

## Сборка и проверка пакета

```bash
uv build
uvx twine check dist/*
```

## Демонстрация

Установка пакета, создание таблицы, проверка сохранения после
перезапуска и удаление таблицы:

[![Демонстрация](https://asciinema.org/a/7xphEuQOQqIFrmdz.svg)](https://asciinema.org/a/7xphEuQOQqIFrmdz)

## Управление таблицами

```text
create_table users name:str age:int is_active:bool
list_tables
info users
drop_table users
```

Типы столбцов: `int`, `str`, `bool`. Имена таблиц и столбцов должны быть
идентификаторами Python. Регистр имеет значение. `ID:int` добавляется
автоматически в начало схемы; повторяющиеся столбцы запрещены.
`drop_table` удаляет и схему, и файл записей таблицы.

## CRUD-операции

Запуск: `uv run database` или `database` после установки wheel.

```text
create_table users name:str age:int is_active:bool
insert into users values ("Sergei", 28, true)
select from users
select from users where age = 28
update users set age = 29 where name = "Sergei"
update users set age = 30, is_active = false where ID = 1
info users
delete from users where ID = 1
help
exit
```

- Все поля обязательны. При `insert` передавайте значения в порядке схемы,
  без ID. Новый ID — максимальный ID среди текущих записей плюс один
  (для пустой таблицы — 1). После удаления максимального ID он может
  использоваться повторно. Уже существующие записи всегда имеют разные ID.
- Строки заключайте в одинарные или двойные кавычки. Пробелы, запятые
  и слово `where` внутри кавычек являются частью строки.
- Целые числа вводятся без кавычек, логические значения — `true` или `false`.
  Типы проверяются строго: `true` не является допустимым значением `int`.
- `where` поддерживает одно условие равенства. `update` и `delete`
  обрабатывают все совпавшие записи и требуют условие. Менять ID нельзя.
- `select` без условия показывает все записи через PrettyTable;
  `info` выводит схему и количество записей.
- Метаданные хранятся в `db_meta.json`, записи — в `data/<таблица>.json`.
  Пути отсчитываются от текущей папки запуска, поэтому запускайте программу
  из одной папки, чтобы пользоваться той же базой. JSON-файлы не входят в Git.
- Это учебная база для одного процесса, без транзакций и параллельной записи.

## Проверка

```bash
uv run ruff check .
uv run python -m unittest discover -s tests -v
uv build
uvx twine check dist/primitive_db-0.4.0*
```

## Запись демонстрации CRUD

```bash
export ASCIINEMA_CONFIG_HOME="$HOME/.asciinema-config"
uvx asciinema rec crud-demo.cast
```

Внутри записи установите wheel и запустите программу:

```bash
uv tool install --force dist/primitive_db-0.4.0-py3-none-any.whl
database
```

В программе выполните создание таблицы `crud_demo`, вставку, выборку,
обновление, `info` и выход. Перезапустите `database`, проверьте сохранение,
удалите запись и таблицу. После выхода из программы введите ещё один `exit`
в оболочке, чтобы закончить запись. Затем загрузите её:

```bash
uvx asciinema upload crud-demo.cast
```

Добавьте ссылку на опубликованную демонстрацию в этот README.

## Демонстрация CRUD

Добавление, выборка, обновление и удаление записей,
а также проверка сохранения данных после перезапуска:

[![Демонстрация CRUD](https://asciinema.org/a/ShWdKS4VfjsY9lMM.svg)](https://asciinema.org/a/ShWdKS4VfjsY9lMM)