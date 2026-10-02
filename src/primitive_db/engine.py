import prompt


def print_help():
    print("\n<command> exit — выйти из программы")
    print("<command> help — справочная информация")


def welcome():
    print("Первая попытка запустить проект!")
    print("\n***")
    print_help()

    while True:
        command = prompt.string("Введите команду: ").strip()

        if not command:
            continue

        if command == "exit":
            print("До свидания!")
            break
        elif command == "help":
            print_help()
        else:
            print(f"Неизвестная команда: {command}. Введите help.")
