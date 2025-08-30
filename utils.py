# @contextmanager
# def decorator_logic(*args, **kwargs):
#     """
#     Context manager to handle decorator logic.
#     This is a placeholder for any logic that needs to be executed
#     before and after the decorated function call.
#     """
#     log.debug("Logic before the function call")
#     result = yield
#     log.debug("Logic after the function call")
#     # Logic after the function call

import asyncio
import functools
from contextlib import contextmanager
import json
import logging
log = logging.getLogger(__name__)

# class DontCallWrapped(Exception):
#     """
#     Exception to indicate that the wrapped function should not be called.
#     This can be used to skip the function execution in certain cases.
#     """
#     def __init__(self, result):
#         self.result = result
    

def sync_async_decorator(decorator_logic):
    """
    A decorator that can handle both synchronous and asynchronous functions.
    It uses a context manager to execute logic before and after the function call.
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):

                gen = decorator_logic(func, *args, **kwargs)
                try:
                    log.debug("calling next(gen)")
                    val = next(gen)
                    # val is the modified args, kwargs
                    log.debug("val:", val)
                except StopIteration as exc:
                    log.debug("Decorator logic did not yield any value, returning early")
                    return exc.value
                args, kwargs = val
                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    log.debug(f"Exception in function {func.__name__}: {e}")
                    raise
                try:
                    log.debug("Sending result back to generator:", result)
                    tmp = gen.send(result)  # Send the function result back to the generator
                    log.debug("tmp:", tmp)
                    # next(gen)
                    raise RuntimeError("generator didn't stop")
                except StopIteration as exc:
                    # receive the return value from the generator
                    log.debug("Decorator logic completed successfully, result:", result)
                    log.debug("exc.value:", exc.value)
                    return exc.value

        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                gen = decorator_logic(func, *args, **kwargs)
                try:
                    log.debug("calling next(gen)")
                    val = next(gen)
                    log.debug("val:", val)
                except StopIteration as exc:
                    log.debug("Decorator logic did not yield any value, returning early")
                    return exc.value
                args, kwargs = val
                try:
                    result = func(*args, **kwargs)
                except Exception as e:
                    log.debug(f"Exception in function {func.__name__}: {e}")
                    raise
                try:
                    log.debug("Sending result back to generator:", result)
                    tmp = gen.send(result)  # Send the result back to the generator
                    log.debug("tmp:", tmp)
                    # next(gen)
                    raise RuntimeError("generator didn't stop")
                except StopIteration as exc:
                    log.debug("Decorator logic completed successfully, result:", result)
                    log.debug("exc.value:", exc.value)
                    return exc.value
        return wrapper
    return decorator


def parse_json_objects(filename):
    """
    Parst JSON-Objekte aus einer Datei, die mehrere JSON-Objekte enthält
    (nicht durch Zeilenumbrüche getrennt), von öffnender zu schließender Klammer.
    """

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    i = 0
    while i < len(content):
        # Überspringe Whitespace
        while i < len(content) and content[i].isspace():
            i += 1

        if i >= len(content):
            break

        # Suche nach öffnender Klammer
        if content[i] == '{':
            start = i
            brace_count = 0
            in_string = False
            escape_next = False

            while i < len(content):
                char = content[i]

                if escape_next:
                    escape_next = False
                elif char == '\\':
                    escape_next = True
                elif char == '"' and not escape_next:
                    in_string = not in_string
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Gefunden: komplettes JSON-Objekt
                            json_str = content[start:i+1]
                            try:
                                json_obj = json.loads(json_str)
                                yield json_obj
                            except json.JSONDecodeError as e:
                                print(f"Fehler beim Parsen von JSON: {e}")
                                print(f"JSON-String: {json_str[:100]}...")
                            break

                i += 1

        i += 1

    # cm = contextmanager(decorator_logic)
    # def decorator(func):
    #     if asyncio.iscoroutinefunction(func):
    #         @functools.wraps(func)
    #         async def wrapper(*args, **kwargs):
    #             with cm(func, *args, **kwargs) as modified_args:
    #                 args, kwargs = modified_args
    #                 return await func(*args, **kwargs)
    #     else:
    #         @functools.wraps(func)
    #         def wrapper(*args, **kwargs):
    #             with cm(func, *args, **kwargs) as modified_args:
    #                 args, kwargs = modified_args
    #                 return func(*args, **kwargs)
    #     return wrapper
    # return decorator