import wavelink
import inspect

print(f"Wavelink version: {wavelink.__version__}")
try:
    sig = inspect.signature(wavelink.Node)
    print(f"Node signature: {sig}")
except Exception as e:
    print(f"Error inspecting Node: {e}")

try:
    sig = inspect.signature(wavelink.Pool.connect)
    print(f"Pool.connect signature: {sig}")
except Exception as e:
    print(f"Error inspecting Pool.connect: {e}")
