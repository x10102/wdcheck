def print_application_number(number: int) -> str:
    if number == 0:
        return "Žádné nové žádosti"
    elif number == 1:
        return "1 nová žádost"
    elif number < 5:
        return f"{number} nové žádosti"
    else:
        return f"{number} nových žádostí"