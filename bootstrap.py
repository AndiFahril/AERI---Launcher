"""Record startup failures beside the EXE, including dependency import errors."""
import sys
import traceback
from pathlib import Path

try:
    import main
    result=main.main()
    if isinstance(result,int):sys.exit(result)
except Exception:
    target = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
    (target / 'AERI-error.log').write_text(traceback.format_exc(), encoding='utf-8')
    raise
