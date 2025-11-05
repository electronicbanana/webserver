
from lights import set_light_power_all

def _run_command(cmd : str) -> str:

    if cmd == "/ping":
        return "Pong from the Grid."
    
    if cmd == "/time":
        return f"Cycle time: {_now()}"
    
    if cmd == "/clear":
        return "cleared history"

    if cmd == "/lights on":
        set_light_power_all(True)
        return "Setting lights on!"

    if cmd == "/lights off":
        set_light_power_all(False)
        return "Setting Lights off!"

    return "Command not found!"


if (__name__ == "__main__"):
	pass