"""Start the optional Wake-on-LAN relay service on port 8780."""
from phone_link.wake_relay import main


if __name__ == "__main__":
    raise SystemExit(main())
