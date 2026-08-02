import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, Canvas, Label, StringVar, Tk, messagebox, ttk

from dotenv import dotenv_values, load_dotenv
from PIL import Image, ImageTk
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

try:
    import pystray
except ModuleNotFoundError:
    pystray = None

try:
    from waitress import serve
except ModuleNotFoundError:
    serve = None

os.environ["PYTHONWARNINGS"] = "ignore"

HOST = "0.0.0.0"
DEFAULT_PORT = 5000
APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
ENV_PATH = APP_DIR / ".env"
ENV_TEMPLATE_PATH = (
    APP_DIR / ".env.example"
    if (APP_DIR / ".env.example").exists()
    else RESOURCE_DIR / ".env.example"
)
LOG_PATH = APP_DIR / "launcher.log"
SINGLE_INSTANCE_SOCKET = None
APP_STATE = {"port": DEFAULT_PORT}

os.chdir(APP_DIR)

pathex=[os.getcwd()]


def setup_runtime_logging() -> None:
    if not getattr(sys, "frozen", False):
        return
    try:
        log_file = LOG_PATH.open("a", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        print("\n" + "=" * 80)
        print(time.strftime("Launcher started at %Y-%m-%d %H:%M:%S"))
        print(f"APP_DIR={APP_DIR}")
        print(f"RESOURCE_DIR={RESOURCE_DIR}")
    except Exception:
        pass

def resource_path(relative_path: str) -> str:
    return str((RESOURCE_DIR / relative_path).resolve())


def resource_exists(relative_path: str) -> bool:
    return (RESOURCE_DIR / relative_path).exists()


def load_runtime_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)


def set_window_icon(window: Tk) -> None:
    try:
        window.iconbitmap(resource_path("icon.ico"))
    except Exception:
        pass


def read_env_values() -> dict[str, str]:
    source = ENV_PATH if ENV_PATH.exists() else ENV_TEMPLATE_PATH
    if not source.exists():
        return {}
    values = {}
    for key, value in dotenv_values(source).items():
        if value is not None:
            values[key] = str(value)
    return values


def format_env_value(value: str) -> str:
    text_value = str(value)
    if any(ch in text_value for ch in [' ', '#', '"', "\n", "\t"]):
        escaped = text_value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text_value


def write_env_values(values: dict[str, str]) -> None:
    ordered_keys = [
        "FLASK_APP",
        "FLASK_ENV",
        "APP_MODE",
        "SECRET_KEY",
        "DATABASE_URL",
        "COMPANY_NAME",
        "COMPANY_ADDRESS",
        "COMPANY_PHONE",
        "COMPANY_TAX_CODE",
        "COMPANY_EMAIL",
        "PORT",
    ]
    lines = [
        "# ERPmini runtime configuration",
        "# File nay duoc launcher.exe cap nhat tu dong.",
        "",
    ]
    for key in ordered_keys:
        value = values.get(key)
        if value:
            lines.append(f"{key}={format_env_value(value)}")

    remaining = sorted(key for key in values if key not in ordered_keys)
    if remaining:
        lines.append("")
        for key in remaining:
            value = values.get(key)
            if value:
                lines.append(f"{key}={format_env_value(value)}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_port(value: str | int | None) -> int:
    try:
        port = int(value or DEFAULT_PORT)
        if 1 <= port <= 65535:
            return port
    except (TypeError, ValueError):
        pass
    return DEFAULT_PORT


def parse_database_url(db_url: str | None) -> dict[str, str]:
    defaults = {
        "host": "localhost",
        "port": "5432",
        "name": "erpmini",
        "user": "postgres",
        "password": "",
    }
    if not db_url:
        return defaults
    try:
        parsed = make_url(db_url)
        return {
            "host": parsed.host or defaults["host"],
            "port": str(parsed.port or defaults["port"]),
            "name": parsed.database or defaults["name"],
            "user": parsed.username or defaults["user"],
            "password": parsed.password or defaults["password"],
        }
    except Exception:
        return defaults


def build_database_url(cfg: dict[str, str]) -> str:
    url = URL.create(
        "postgresql",
        username=cfg["user"].strip(),
        password=cfg["password"],
        host=cfg["host"].strip(),
        port=normalize_port(cfg["port"]),
        database=cfg["name"].strip(),
    )
    return url.render_as_string(hide_password=False)


def build_admin_database_url(cfg: dict[str, str]) -> str:
    url = URL.create(
        "postgresql",
        username=cfg["user"].strip(),
        password=cfg["password"],
        host=cfg["host"].strip(),
        port=normalize_port(cfg["port"]),
        database="postgres",
    )
    return url.render_as_string(hide_password=False)


def test_database_connection(cfg: dict[str, str]) -> tuple[bool, str, str]:
    engine = None
    try:
        engine = create_engine(build_database_url(cfg), future=True, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Kết nối PostgreSQL thành công.", "ok"
    except SQLAlchemyError as exc:
        message = str(getattr(exc, "orig", exc)).strip() or str(exc)
        lowered = message.lower()
        if "does not exist" in lowered and "database" in lowered:
            return False, f"Database '{cfg['name']}' chưa tồn tại.", "missing_database"
        if "password authentication failed" in lowered:
            return False, "Sai username hoặc password PostgreSQL.", "auth_error"
        if "connection refused" in lowered:
            return False, "Không kết nối được đến PostgreSQL server.", "connection_refused"
        return False, message, "error"
    finally:
        if engine is not None:
            engine.dispose()


def create_database(cfg: dict[str, str]) -> tuple[bool, str]:
    engine = None
    try:
        engine = create_engine(
            build_admin_database_url(cfg),
            future=True,
            isolation_level="AUTOCOMMIT",
            pool_pre_ping=True,
        )
        db_name = cfg["name"].strip()
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            ).scalar()
            if exists:
                return True, f"Database '{db_name}' đã tồn tại."

            safe_name = db_name.replace('"', '""')
            conn.exec_driver_sql(f'CREATE DATABASE "{safe_name}" ENCODING \'UTF8\'')
        return True, f"Đã tạo database '{db_name}'."
    except SQLAlchemyError as exc:
        message = str(getattr(exc, "orig", exc)).strip() or str(exc)
        return False, message
    finally:
        if engine is not None:
            engine.dispose()


def database_is_initialized(cfg: dict[str, str]) -> bool:
    engine = None
    try:
        engine = create_engine(build_database_url(cfg), future=True, pool_pre_ping=True)
        with engine.connect() as conn:
            users_exists = conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'users'
                    )
                    """
                )
            ).scalar()
        return bool(users_exists)
    except SQLAlchemyError:
        return False
    finally:
        if engine is not None:
            engine.dispose()


def initialize_database() -> tuple[bool, str]:
    try:
        import init_db

        init_db.init_database()
        return True, "Đã khởi tạo bảng dữ liệu và dữ liệu mẫu."
    except Exception as exc:
        return False, str(exc)


def maybe_initialize_database(cfg: dict[str, str]) -> bool:
    if database_is_initialized(cfg):
        return True

    wants_init = messagebox.askyesno(
        "Khởi tạo database",
        (
            "Database đã kết nối thành công nhưng chưa có bảng dữ liệu.\n\n"
            "Bạn có muốn tạo bảng và dữ liệu mẫu ngay bây giờ không?"
        ),
    )
    if not wants_init:
        return True

    ok, message = initialize_database()
    if ok:
        messagebox.showinfo("Khởi tạo thành công", message)
        return True

    messagebox.showerror(
        "Khởi tạo thất bại",
        f"{message}\n\nBạn có thể chạy init_db.py thủ công sau.",
    )
    return False


def ensure_secret_key(values: dict[str, str]) -> None:
    if not values.get("SECRET_KEY"):
        values["SECRET_KEY"] = secrets.token_hex(32)


def save_runtime_config(db_cfg: dict[str, str], app_port: str) -> None:
    values = read_env_values()
    values.setdefault("FLASK_APP", "run.py")
    values.setdefault("FLASK_ENV", "production")
    values.setdefault("APP_MODE", "prod")
    values.setdefault("COMPANY_NAME", "Công ty TNHH Công Nghệ Việt")
    values.setdefault("COMPANY_ADDRESS", "123 Đường ABC, TP.HCM")
    values.setdefault("COMPANY_PHONE", "0903671304")
    values.setdefault("COMPANY_TAX_CODE", "0312345678")
    values.setdefault("COMPANY_EMAIL", "caytrebm@gmail.com")
    values["DATABASE_URL"] = build_database_url(db_cfg)
    values["PORT"] = str(normalize_port(app_port))
    ensure_secret_key(values)
    write_env_values(values)

    os.environ["DATABASE_URL"] = values["DATABASE_URL"]
    os.environ["PORT"] = values["PORT"]
    os.environ["FLASK_ENV"] = values["FLASK_ENV"]
    os.environ["APP_MODE"] = values["APP_MODE"]
    os.environ["SECRET_KEY"] = values["SECRET_KEY"]


def restart_launcher(icon=None) -> None:
    if icon is not None:
        try:
            icon.stop()
        except Exception:
            pass

    if getattr(sys, "frozen", False):
        os.execl(sys.executable, sys.executable, *sys.argv[1:])
    os.execl(sys.executable, sys.executable, *sys.argv)


def prompt_database_setup(
    db_cfg: dict[str, str],
    app_port: str,
    error_message: str | None = None,
    window_title: str = "ERP-VIET - Cấu hình kết nối dữ liệu",
    intro_text: str = "Nhập thông tin PostgreSQL để khởi động ERP trên máy mới.",
    save_button_text: str = "Lưu và khởi động",
) -> tuple[dict[str, str], str] | None:
    result: dict[str, str] = {}

    root = Tk()
    root.title(window_title)
    root.geometry("660x520")
    root.minsize(560, 420)
    root.resizable(True, True)
    root.configure(bg="#f4f7fb")
    set_window_icon(root)
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))

    container = ttk.Frame(root)
    container.pack(fill="both", expand=True)
    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)

    canvas = Canvas(
        container,
        background="#f4f7fb",
        highlightthickness=0,
        bd=0,
    )
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    frame = ttk.Frame(canvas, padding=18)
    frame.columnconfigure(0, weight=1)
    canvas_window = canvas.create_window((0, 0), window=frame, anchor="nw")

    footer = ttk.Frame(container, padding=(18, 10, 18, 16))
    footer.grid(row=1, column=0, columnspan=2, sticky="ew")

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("LauncherTitle.TLabel", font=("Segoe UI", 14, "bold"))
    style.configure("LauncherHint.TLabel", foreground="#475569")
    style.configure("LauncherInfo.TLabel", foreground="#64748b")
    style.configure("LauncherStatus.TLabelframe.Label", font=("Segoe UI", 10, "bold"))

    ttk.Label(
        frame,
        text="Cấu hình kết nối dữ liệu cho ERP-VIET",
        style="LauncherTitle.TLabel",
    ).grid(row=0, column=0, sticky="w")

    ttk.Label(
        frame,
        text=intro_text,
        style="LauncherHint.TLabel",
    ).grid(row=1, column=0, sticky="w", pady=(4, 4))

    ttk.Label(
        frame,
        text=f"File cấu hình được lưu tại: {ENV_PATH}",
        style="LauncherInfo.TLabel",
    ).grid(row=2, column=0, sticky="w", pady=(0, 12))

    status_var = StringVar(
        value=error_message
        or f"Launcher sẽ lưu cấu hình vào: {ENV_PATH}"
    )

    field_vars = {
        "host": StringVar(value=db_cfg.get("host", "localhost")),
        "port": StringVar(value=db_cfg.get("port", "5432")),
        "name": StringVar(value=db_cfg.get("name", "erpmini")),
        "user": StringVar(value=db_cfg.get("user", "postgres")),
        "password": StringVar(value=db_cfg.get("password", "")),
        "app_port": StringVar(value=str(normalize_port(app_port))),
    }
    show_password_var = BooleanVar(value=False)

    db_fields = [
        ("Host PostgreSQL", "host"),
        ("Port PostgreSQL", "port"),
        ("Tên database", "name"),
        ("Username", "user"),
        ("Password", "password"),
    ]
    app_fields = [
        ("Port ứng dụng", "app_port"),
    ]

    db_frame = ttk.LabelFrame(frame, text="Thông tin PostgreSQL", padding=14)
    db_frame.grid(row=3, column=0, sticky="ew")
    db_frame.columnconfigure(1, weight=1)

    password_entry = None
    first_entry = None

    for idx, (label_text, key) in enumerate(db_fields):
        ttk.Label(db_frame, text=label_text).grid(
            row=idx, column=0, sticky="w", pady=6, padx=(0, 12)
        )
        show_value = "*" if key == "password" else ""
        entry = ttk.Entry(db_frame, textvariable=field_vars[key], show=show_value)
        entry.grid(row=idx, column=1, sticky="ew", pady=6)
        if first_entry is None:
            first_entry = entry
        if key == "password":
            password_entry = entry

    def toggle_password() -> None:
        if password_entry is None:
            return
        password_entry.configure(show="" if show_password_var.get() else "*")

    ttk.Checkbutton(
        db_frame,
        text="Hiện mật khẩu",
        variable=show_password_var,
        command=toggle_password,
    ).grid(row=len(db_fields), column=1, sticky="w", pady=(2, 0))

    ttk.Label(
        db_frame,
        text="Bạn có thể dùng localhost nếu PostgreSQL nằm trên cùng máy .",
        style="LauncherInfo.TLabel",
    ).grid(row=len(db_fields) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    app_frame = ttk.LabelFrame(frame, text="Thông tin ứng dụng", padding=14)
    app_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))
    app_frame.columnconfigure(1, weight=1)

    for idx, (label_text, key) in enumerate(app_fields):
        ttk.Label(app_frame, text=label_text).grid(
            row=idx, column=0, sticky="w", pady=6, padx=(0, 12)
        )
        entry = ttk.Entry(app_frame, textvariable=field_vars[key])
        entry.grid(row=idx, column=1, sticky="ew", pady=6)

    ttk.Label(
        app_frame,
        text="Đổi port nếu máy đã có ứng dụng khác dùng cổng 5000.",
        style="LauncherInfo.TLabel",
    ).grid(row=len(app_fields), column=0, columnspan=2, sticky="w", pady=(8, 0))

    status_box = ttk.LabelFrame(frame, text="Trạng thái", padding=14, style="LauncherStatus.TLabelframe")
    status_box.grid(row=5, column=0, sticky="ew", pady=(12, 0))

    status_label = ttk.Label(
        status_box,
        textvariable=status_var,
        foreground="#b45309" if error_message else "#475569",
        wraplength=560,
        justify="left",
    )
    status_label.grid(row=0, column=0, sticky="w")

    def set_status(message: str, color: str) -> None:
        status_var.set(message)
        status_label.configure(foreground=color)

    def collect_cfg() -> tuple[dict[str, str], str]:
        cfg = {
            "host": field_vars["host"].get().strip() or "localhost",
            "port": field_vars["port"].get().strip() or "5432",
            "name": field_vars["name"].get().strip() or "erpmini",
            "user": field_vars["user"].get().strip() or "postgres",
            "password": field_vars["password"].get(),
        }
        return cfg, field_vars["app_port"].get().strip() or str(DEFAULT_PORT)

    def try_connect(allow_create: bool) -> tuple[bool, dict[str, str] | None, str | None]:
        cfg, selected_port = collect_cfg()
        ok, message, status = test_database_connection(cfg)
        if ok:
            set_status(message, "#15803d")
            return True, cfg | {"app_port": selected_port}, None

        if status == "missing_database" and allow_create:
            wants_create = messagebox.askyesno(
                "Tao database",
                f"{message}\n\nBạn có muốn tạo database này ngay bây giờ không?",
                parent=root,
            )
            if wants_create:
                created, create_message = create_database(cfg)
                if not created:
                    set_status(create_message, "#b91c1c")
                    messagebox.showerror(
                        "Không tọo được database",
                        create_message,
                        parent=root,
                    )
                    return False, None, None

                ok, message, status = test_database_connection(cfg)
                if ok:
                    set_status(create_message, "#15803d")
                    return True, cfg | {"app_port": selected_port}, None

        set_status(message, "#b91c1c")
        return False, None, status

    def on_test() -> None:
        try_connect(allow_create=True)

    def on_save() -> None:
        ok, payload, _ = try_connect(allow_create=True)
        if not ok or payload is None:
            return
        result.update(payload)
        root.destroy()

    def on_cancel() -> None:
        root.destroy()

    def sync_scroll_region(event=None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def sync_canvas_width(event) -> None:
        canvas.itemconfigure(canvas_window, width=event.width)
        status_label.configure(wraplength=max(360, event.width - 70))

    def on_mousewheel(event) -> None:
        delta = event.delta
        if delta == 0:
            return
        canvas.yview_scroll(int(-delta / 120), "units")

    def bind_mousewheel(_event=None) -> None:
        canvas.bind_all("<MouseWheel>", on_mousewheel)

    def unbind_mousewheel(_event=None) -> None:
        canvas.unbind_all("<MouseWheel>")

    frame.bind("<Configure>", sync_scroll_region)
    canvas.bind("<Configure>", sync_canvas_width)
    canvas.bind("<Enter>", bind_mousewheel)
    canvas.bind("<Leave>", unbind_mousewheel)

    button_row = ttk.Frame(footer)
    button_row.pack(side="right")

    ttk.Button(button_row, text="Kiểm tra kết nối", command=on_test).pack(side="left", padx=(0, 8))
    ttk.Button(button_row, text=save_button_text, command=on_save).pack(side="left", padx=(0, 8))
    ttk.Button(button_row, text="Thoát", command=on_cancel).pack(side="left")

    root.protocol("WM_DELETE_WINDOW", on_cancel)
    if first_entry is not None:
        first_entry.focus_set()
    root.mainloop()

    if not result:
        return None

    saved_cfg = {
        "host": result["host"],
        "port": result["port"],
        "name": result["name"],
        "user": result["user"],
        "password": result["password"],
    }
    return saved_cfg, result["app_port"]


def ensure_database_config() -> int | None:
    load_runtime_env()
    env_values = read_env_values()
    db_cfg = parse_database_url(env_values.get("DATABASE_URL"))
    app_port = env_values.get("PORT", str(DEFAULT_PORT))

    error_message = None
    if env_values.get("DATABASE_URL"):
        ok, message, _ = test_database_connection(db_cfg)
        if ok:
            if not maybe_initialize_database(db_cfg):
                return None
            APP_STATE["port"] = normalize_port(app_port)
            return APP_STATE["port"]
        error_message = f"Không kết nối được DB hiện tại: {message}"
    else:
        error_message = "Chưa tìm thấy cấu hình DATABASE_URL. Vui lòng nhập lại."

    prompt_result = prompt_database_setup(db_cfg, app_port, error_message)
    if prompt_result is None:
        return None

    saved_cfg, saved_port = prompt_result
    save_runtime_config(saved_cfg, saved_port)
    load_runtime_env()

    if not maybe_initialize_database(saved_cfg):
        return None

    APP_STATE["port"] = normalize_port(saved_port)
    return APP_STATE["port"]


def open_runtime_configuration(icon=None, item=None) -> None:
    env_values = read_env_values()
    current_db_cfg = parse_database_url(env_values.get("DATABASE_URL"))
    current_port = env_values.get("PORT", str(APP_STATE["port"]))
    current_url = env_values.get("DATABASE_URL", "")
    current_port_norm = str(normalize_port(current_port))

    prompt_result = prompt_database_setup(
        current_db_cfg,
        current_port,
        window_title="ERP-VIET - Cập nhật kết nối dữ liệu",
        intro_text="Cập nhật thông tin PostgreSQL hoặc đổi cổng ứng dụng cho máy đang sử dụng.",
        save_button_text="Lưu cấu hình lại",
    )
    if prompt_result is None:
        return

    saved_cfg, saved_port = prompt_result
    save_runtime_config(saved_cfg, saved_port)
    load_runtime_env()

    if not maybe_initialize_database(saved_cfg):
        return

    APP_STATE["port"] = normalize_port(saved_port)
    changed = (
        build_database_url(saved_cfg) != current_url
        or str(normalize_port(saved_port)) != current_port_norm
    )

    if not changed:
        messagebox.showinfo(
            "Không có thay đổi",
            "Cấu hình hiện tại đã hợp lệ và không có thay đổi nào cần áp dụng.",
        )
        return

    wants_restart = messagebox.askyesno(
        "Khởi động lại ERP",
        (
            "Đã lưu cấu hình mới thành công.\n\n"
            "Bạn có muốn khởi động lại ERP ngay bây giờ để áp dụng cấu hình mới không?"
        ),
    )
    if wants_restart:
        restart_launcher(icon)
    else:
        messagebox.showinfo(
            "Đã lưu cấu hình",
            "Cấu hình mới sẽ được áp dụng sau khi đóng và mở lại ERP.",
        )


def get_browser_url() -> str:
    return f"http://127.0.0.1:{APP_STATE['port']}"

def ensure_single_instance() -> bool:
    """
    Trả về True nếu là instance đầu tiên.
    Nếu app đã chạy -> mở browser rồi return False
    """
    global SINGLE_INSTANCE_SOCKET

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # port riêng để lock app
        sock.bind(("127.0.0.1", 56789))

        # giữ socket sống
        SINGLE_INSTANCE_SOCKET = sock
        return True

    except OSError:
        # app đã chạy
        try:
            webbrowser.open(get_browser_url())
        except Exception:
            pass

        return False
    
def get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_lan_url() -> str:
    return f"http://{get_local_ip()}:{APP_STATE['port']}"


def open_browser() -> None:
    webbrowser.open(get_browser_url())


def on_open(icon, item) -> None:
    open_browser()


def on_configure(icon, item) -> None:
    open_runtime_configuration(icon, item)


def on_exit(icon, item) -> None:
    global SINGLE_INSTANCE_SOCKET

    try:
        if SINGLE_INSTANCE_SOCKET:
            SINGLE_INSTANCE_SOCKET.close()
    except Exception:
        pass

    icon.stop()
    os._exit(0)


def run_tray() -> None:
    if pystray is None:
        print("pystray chưa được cài đặt. Launcher sẽ giữ server bằng chế độ console.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            os._exit(0)
        return

    try:
        image = Image.open(resource_path("icon.ico"))
    except Exception as exc:
        print("Tray icon load error:", exc)
        image = Image.new("RGB", (64, 64), "#2563eb")
    menu = pystray.Menu(
        pystray.MenuItem("Mở ERP", on_open),
        pystray.MenuItem("Cấu hình dữ liệu", on_configure),
        pystray.MenuItem("Thoát", on_exit),
    )
    icon = pystray.Icon("ERP", image, "ERP System", menu)
    icon.run()


def show_splash() -> None:
    if not resource_exists("splash.png"):
        print("Splash image not found, skipping splash screen.")
        return

    root = Tk()
    root.overrideredirect(True)
    set_window_icon(root)

    width = 400
    height = 250
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    root.geometry(f"{width}x{height}+{x}+{y}")

    try:
        img = Image.open(resource_path("splash.png")).resize((width, height))
    except Exception as exc:
        print("Splash image load error:", exc)
        root.destroy()
        return
    photo = ImageTk.PhotoImage(img)

    label = Label(root, image=photo, borderwidth=0)
    label.image = photo
    label.pack()

    root.after(2200, root.destroy)
    root.mainloop()


def create_runtime_app():
    load_runtime_env()
    from app import create_app
    from app.shop_app import create_shop_app
    from werkzeug.middleware.dispatcher import DispatcherMiddleware

    main_app = create_app(os.getenv("FLASK_ENV", "production"))
    shop = create_shop_app(os.getenv("FLASK_ENV", "production"))
    return DispatcherMiddleware(main_app, {"/shop": shop})


def start_server(app) -> None:
    try:
        print(f"Server running at {get_browser_url()}")
        print(f"Mobile truy cap: {get_lan_url()}")
        if serve is not None:
            serve(app, host=HOST, port=APP_STATE["port"], threads=8)
        else:
            print("waitress chưa được cài đặt. Đang sử dụng Flask built-in server làm fallback.")
            app.run(host=HOST, port=APP_STATE["port"], debug=False, use_reloader=False)
    except Exception as exc:
        print("Server error:", exc)


def main() -> None:

    # nếu app đã chạy thì chỉ mở browser
    if not ensure_single_instance():
        return

    selected_port = ensure_database_config()
    if selected_port is None:
        return

    show_splash()
    app = create_runtime_app()

    server_thread = threading.Thread(
        target=start_server,
        args=(app,),
        daemon=True,
    )
    server_thread.start()

    threading.Thread(
        target=lambda: (time.sleep(1.5), open_browser()),
        daemon=True,
    ).start()

    run_tray()


if __name__ == "__main__":
    setup_runtime_logging()
    try:
        main()
    except Exception as exc:
        print("Launcher error:", exc)
        try:
            messagebox.showerror("Launcher lỗi", str(exc))
        except Exception:
            pass
        raise
