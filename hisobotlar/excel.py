"""Excel (.xlsx) fayl yasash."""
import io
from collections.abc import Iterable, Sequence

from openpyxl import Workbook
from openpyxl.styles import Font


def jadval_xlsx(sarlavhalar: list[str], qatorlar: Iterable[Sequence]) -> bytes:
    """Bitta varaqli jadval: birinchi qator qalin sarlavha."""
    kitob = Workbook(write_only=False)
    varaq = kitob.active
    varaq.append(list(sarlavhalar))
    for yacheyka in varaq[1]:
        yacheyka.font = Font(bold=True)
    for qator in qatorlar:
        varaq.append(list(qator))
    chiqish = io.BytesIO()
    kitob.save(chiqish)
    return chiqish.getvalue()
