import wavelink
import inspect

print(f"Wavelink version: {wavelink.__version__}")
try:
    print("Player attributes:")
    for name, member in inspect.getmembers(wavelink.Player):
        if not name.startswith("_"):
            print(f"- {name}")
except Exception as e:
    print(f"Error inspecting Player: {e}")
