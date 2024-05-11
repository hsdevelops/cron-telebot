from typing import Callable, Coroutine, Any, Optional

MESSAGE_HANDLER = Callable[[Any, Any], Coroutine[Any, Any, Optional[Exception]]]
