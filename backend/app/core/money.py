from typing import Annotated

from pydantic import Field

Paise = Annotated[int, Field(strict=True, ge=0)]


def minimum_advance_paise(total_paise: int, percent: int) -> int:
    """Round the configured minimum up to the nearest whole paise."""
    if type(total_paise) is not int or total_paise < 0:
        raise ValueError("Total must be non-negative integer paise")
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError("Advance percent must be an integer from 0 to 100")
    return (total_paise * percent + 99) // 100
