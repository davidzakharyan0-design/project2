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
uvx twine check dist/primitive_db-0.5.0*
```

## Запись демонстрации CRUD

```bash
export ASCIINEMA_CONFIG_HOME="$HOME/.asciinema-config"
uvx asciinema rec crud-demo.cast
```

Внутри записи установите wheel и запустите программу:

```bash
uv tool install --force dist/primitive_db-0.5.0-py3-none-any.whl
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

## Декораторы и замыкания

Модуль `src/primitive_db/decorators.py` входит в устанавливаемый пакет.
Во всех декораторах используется `functools.wraps`, чтобы сохранить имя,
документацию и доступ к исходной функции через `__wrapped__`.

- `handle_db_errors` обрабатывает `FileNotFoundError`, `KeyError`, `ValueError`,
  ошибки файловой системы и другие исключения. При вложенных вызовах ошибка
  доходит до внешней обёртки, которая печатает её ровно один раз и возвращает
  маркер `DB_ERROR`. Это не позволяет продолжить запись после ошибки проверки.
  `ContextVar` хранит глубину вложенных вызовов; `finally` восстанавливает её.
- `confirm_action(action_name)` — фабрика декораторов. Перед `drop_table`
  и `delete` запрашивает подтверждение. Только точный ответ `y` разрешает
  операцию; любой другой ответ возвращает `CANCELLED`. Движок в этом случае
  не сохраняет данные и не выводит сообщение об успешном удалении.
- `log_time` измеряет `insert` и `select` через `time.monotonic()` и печатает
  длительность с тремя знаками после точки, включая неуспешные вызовы.
- `create_cacher()` возвращает функцию `cache_result(key, value_func)`.
  Словарь находится в замыкании. Повторный ключ возвращает сохранённый результат,
  не вызывая `value_func` повторно. Ошибки не кэшируются. При заполнении
  256 записей кэш очищается; его также можно очистить методом `.clear()`.
- `select` использует этот кэш. Ключ включает снимок текущих данных и условие,
  поэтому после изменения таблицы старый результат не используется.
  Результат возвращается как независимая копия. Файлы по-прежнему читаются,
  и снимок сериализуется при каждом запросе: кэш экономит повторную фильтрацию,
  но для маленьких таблиц ускорение не гарантируется. Он живёт только в памяти.

Пример проверки (ответы `n` и `y` вводятся на запрос подтверждения):

```text
create_table final_demo name:str age:int
insert into final_demo values ("Sergei", 28)
select from final_demo
select from final_demo
update final_demo set age=29 where ID=1
select from final_demo
insert into final_demo values ("Bad", "wrong type")
delete from final_demo where ID=1
n
select from final_demo
delete from final_demo where ID=1
y
info final_demo
drop_table final_demo
n
list_tables
drop_table final_demo
y
exit
```

## Финальная запись

```bash
export ASCIINEMA_CONFIG_HOME="$HOME/.asciinema-config"
uvx asciinema rec decorators-demo.cast
uv tool install --force dist/primitive_db-0.5.0-py3-none-any.whl
database
```

Выполните пример выше. После выхода из базы введите ещё один `exit`,
чтобы завершить запись оболочки. Затем выполните:

```bash
uvx asciinema upload decorators-demo.cast
```

Добавьте ссылку на опубликованную финальную запись в README.

## Демонстрация декораторов и замыканий

Обработка ошибок, замер времени, повторные запросы,
отмена и подтверждение удаления:

[![Финальная демонстрация](https://asciinema.org/a/VFTA3f86vF4odhhB.svg)](https://asciinema.org/a/VFTA3f86vF4odhhB)