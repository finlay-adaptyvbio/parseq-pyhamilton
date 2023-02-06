import os, json


def recover_state(path) -> dict:
    state = load_state(path)

    while True:
        print_state(state)
        question = input(
            "Are there any values to set manually? (type # or 0 for none): "
        )
        try:
            answer = int(question)
            if answer in range(1, len(state.keys()) + 1):
                key = list(state.keys())[answer - 1]
                value = input(f"Enter a new value for {key}: ")
                while True:
                    try:
                        reset_state(state, path, key, int(value))
                    except ValueError:
                        continue
                    break
            elif answer == 0:
                break
            continue
        except ValueError:
            continue
    return state


def load_state(path) -> dict:
    try:
        with open(path, "r") as f:
            state = json.load(f)
        return state
    except (FileNotFoundError, IsADirectoryError) as e:
        raise e


def save_state(state, path):
    with open(path, "w") as f:
        json.dump(state, f, indent=4)


def update_state(state, path, key, value):
    state[key] += value
    save_state(state, path)
    return state


def reset_state(state, path, key, value):
    state[key] = value
    save_state(state, path)
    return state


def print_state(state):
    print(f"{'-' * 40}")
    print(f"{'#':<5}{'Key':<25}{'Value':<25}")
    print(f"{'-' * 40}")
    for idx, key in enumerate(state.keys()):
        print(f"{idx + 1:<5}{key:<25}{state[key]:<25}")
    print(f"{'-' * 40}")


def dump_state(state):
    print(json.dumps(state, indent=4))
