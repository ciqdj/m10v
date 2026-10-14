"""Start m10v on a random loopback port."""

from pathlib import Path
import webbrowser

from m10v_core.api import create_server
from m10v_core.storage import Store


def main():
    store = Store(Path(__file__).resolve().parent / 'data')
    server = create_server(store)
    url = f'http://127.0.0.1:{server.server_port}/'
    print(url, flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
