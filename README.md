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