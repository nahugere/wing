import asyncio
import sys
from wing import Wing
from presets import Preset, Presets

WING = Wing()


if __name__ == "__main__":
    arg1 = sys.argv[1]

    try:
        match arg1:
            case "create":
                arg2 = sys.argv[2]
                WING.create(arg2)
            case "list":
                WING.list_projects()
            case "start":
                arg2 = sys.argv[2]
                arg3 = sys.argv[3]
                asyncio.run(WING.start(arg2, arg3, Presets(0) if "-flutter" in sys.argv else None))
            case "help":
                WING.help()
            case "version":
                WING.version()
            case _:
                print("Command was not recognized")
    except KeyboardInterrupt:
        print("\nHave a blessed day!")
    except Exception as e:
        print(e)
