import os, json

STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def load_state():
    with open(STATE_FILE_PATH, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE_PATH, "w") as f:
        json.dump(state, f)


def update_state(state, key, value):
    state[key] += value
    save_state(state)


def reset_state(state, key, value):
    state[key] = value
    save_state(state)
