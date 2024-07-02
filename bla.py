def example_function():
    try:
        # Some code that may raise an exception
        x = 1 / 0
    except ZeroDivisionError:
        print("Caught ZeroDivisionError")

    print("This should not print if OSError is raised")


try:
    example_function()
except OSError as e:
    print(f"Caught an OSError: {e}")

print("Execution continues here if OSError is caught")
