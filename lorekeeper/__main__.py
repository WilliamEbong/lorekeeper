if not __package__:   # run as a folder or file, e.g. python _system/vendor/lorekeeper wiki
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path[:] = [os.path.dirname(here)] + [p for p in sys.path if os.path.abspath(p or ".") != here]
    from lorekeeper.cli import main
else:
    from .cli import main

raise SystemExit(main())
