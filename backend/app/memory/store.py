from collections import defaultdict


conversation_history = defaultdict(list)
active_state = defaultdict(lambda: None)


def add_message(session_id, role, content):

    conversation_history[session_id].append({
        "role": role,
        "content": content
    })


def get_history(session_id):

    return conversation_history[session_id][-6:]


def set_active_state(session_id, state):

    active_state[session_id] = state


def get_active_state(session_id):

    return active_state[session_id]
