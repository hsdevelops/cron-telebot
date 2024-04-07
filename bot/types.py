from typing import Callable, Coroutine, Any

MESSAGE_HANDLER = Callable[[Any, Any],  Coroutine[Any, Any, Exception | None]]
