import customtkinter as ctk

from ui import theme
from ui.main_window import MainWindow
from ui.intro import GhostIntro


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    theme.load_active_theme()

    app = MainWindow()
    app.update_idletasks()

    def start_intro():
        try:
            intro = GhostIntro(app, on_done=app.focus_force)
            intro.play()
        except Exception:
            import traceback
            traceback.print_exc()

    app.after(80, start_intro)
    app.mainloop()


if __name__ == "__main__":
    main()