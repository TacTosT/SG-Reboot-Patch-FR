"""STEINS;GATE RE:BOOT - Patch FR : installeur graphique.

Un seul écran : le dossier du jeu (détecté tout seul), un bouton pour
installer, un bouton pour revenir en arrière. Le travail lourd tourne dans un thread pour
que la fenetre reste vivante, et remonte ses nouvelles par une file d'attente.

    python patcher.py            # lance l'interface
    python patcher.py --install  # sans interface, pour les tests
"""
import os
import queue
import sys
import threading
import traceback

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sgre_patch import locate, patch

VERSION = "1.1"
CREDITS = "Traduction française par Astate"
TITLE = "STEINS;GATE RE:BOOT — Patch français"

BG = "#14161c"
PANEL = "#1c1f28"
FG = "#e6e8ee"
MUTED = "#8b91a3"
ACCENT = "#e0a33e"
ACCENT_DIM = "#a8802f"
OK = "#5dcf7f"
BAD = "#e06c6c"


def resource(*parts):
    """Path to a bundled file, whether running from source or from the .exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


FR_FILE = resource("data", "all_fr.jsonl")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        icon = resource("icon.ico")
        if os.path.isfile(icon):
            try:
                self.iconbitmap(icon)
            except tk.TclError:
                pass
        self.events = queue.Queue()
        self.worker = None
        self.stop_flag = False
        self.game_dir = tk.StringVar()

        self._build_ui()
        self._style()
        self.after(60, self._pump)
        self.after(100, self._autodetect)

    # ---------------------------------------------------------------- layout

    def _build_ui(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(head, text="STEINS;GATE RE:BOOT", bg=BG, fg=FG,
                 font=("Segoe UI Semibold", 17)).pack(anchor="w")
        tk.Label(head, text="Patch de traduction française  —  v" + VERSION,
                 bg=BG, fg=ACCENT, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        box = tk.Frame(self, bg=PANEL, highlightthickness=1,
                       highlightbackground="#2b2f3b")
        box.pack(fill="x", padx=24, pady=16)

        tk.Label(box, text="Dossier du jeu", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w",
                                            padx=14, pady=(12, 2))
        entry = tk.Entry(box, textvariable=self.game_dir, bg="#12141a", fg=FG,
                         insertbackground=FG, relief="flat",
                         font=("Consolas", 9), width=62)
        entry.grid(row=1, column=0, sticky="we", padx=(14, 8), ipady=5)
        ttk.Button(box, text="Parcourir...", command=self._browse,
                   style="Sec.TButton").grid(row=1, column=1, padx=(0, 14))
        box.columnconfigure(0, weight=1)

        self.status = tk.Label(box, text="Recherche du jeu...", bg=PANEL, fg=MUTED,
                               font=("Segoe UI", 9), anchor="w")
        self.status.grid(row=2, column=0, columnspan=2, sticky="we",
                         padx=14, pady=(8, 12))

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=24)
        self.btn_install = ttk.Button(actions, text="Installer la traduction FR",
                                      command=self._install, style="Go.TButton")
        self.btn_install.pack(side="left", ipadx=10, ipady=6)
        self.btn_restore = ttk.Button(actions, text="Restaurer l'original",
                                      command=self._restore, style="Sec.TButton")
        self.btn_restore.pack(side="left", padx=10, ipady=6)

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=1000,
                                        style="Go.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=24, pady=(16, 4))
        self.step = tk.Label(self, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9),
                             anchor="w")
        self.step.pack(fill="x", padx=24)

        self.log = tk.Text(self, height=9, bg="#101219", fg=MUTED, relief="flat",
                           font=("Consolas", 8), wrap="word", state="disabled",
                           padx=10, pady=8)
        self.log.pack(fill="both", expand=True, padx=24, pady=(10, 6))
        self.log.tag_configure("ok", foreground=OK)
        self.log.tag_configure("bad", foreground=BAD)
        self.log.tag_configure("hi", foreground=ACCENT)

        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(foot, text=CREDITS + "  ·  patch non officiel, sans lien "
                 "avec MAGES./5pb.", bg=BG, fg="#5d6272",
                 font=("Segoe UI", 8)).pack(side="left")
        help_link = tk.Label(foot, text="Aide", bg=BG, fg=ACCENT_DIM,
                             font=("Segoe UI", 8, "underline"), cursor="hand2")
        help_link.pack(side="right")
        help_link.bind("<Button-1>", lambda _e: self._help())

    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Go.TButton", background=ACCENT, foreground="#1a1206",
                    font=("Segoe UI Semibold", 10), borderwidth=0, focuscolor=ACCENT)
        s.map("Go.TButton", background=[("active", "#f0b755"), ("disabled", "#4a412c")],
              foreground=[("disabled", "#8a8474")])
        s.configure("Sec.TButton", background="#2b3040", foreground=FG,
                    font=("Segoe UI", 10), borderwidth=0, focuscolor="#2b3040")
        s.map("Sec.TButton", background=[("active", "#39405420"), ("disabled", "#22252f")],
              foreground=[("disabled", "#565b6a")])
        s.configure("Go.Horizontal.TProgressbar", troughcolor="#101219",
                    background=ACCENT, borderwidth=0, thickness=8)

    # ------------------------------------------------------------- utilities

    def say(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_install.configure(state=state)
        self.btn_restore.configure(state=state)

    def _help(self):
        messagebox.showinfo(
            "Aide",
            "1. Le programme trouve le jeu tout seul. Sinon, cliquez sur "
            "« Parcourir... » et choisissez le dossier "
            "SGRE\\wind3d11data.\n\n"
            "2. Cliquez sur « Installer la traduction FR ». Les fichiers "
            "d'origine sont sauvegardés automatiquement dans "
            "wind3d11data\\_fr_backup.\n\n"
            "3. Dans le jeu, mettez la langue sur ENGLISH : le français s'affiche "
            "à la place de l'anglais.\n\n"
            "Pour revenir en arrière : bouton « Restaurer l'original », "
            "ou Steam > clic droit sur le jeu > Propriétés > Fichiers installés > "
            "Vérifier l'intégrité des fichiers.\n\n"
            "Une mise à jour du jeu peut écraser le patch : il suffit de le "
            "réinstaller.",
            parent=self)

    # ------------------------------------------------------------- detection

    def _autodetect(self):
        found = locate.candidates()
        if found:
            self.game_dir.set(found[0])
            self.say("Jeu détecté : " + found[0])
            if len(found) > 1:
                self.say("(" + str(len(found) - 1) + " autre(s) installation(s) "
                         "trouvée(s) — changez le dossier si besoin)")
        else:
            self.say("Jeu introuvable automatiquement. Utilisez "
                     "« Parcourir... ».", "bad")
        if not os.path.isfile(FR_FILE):
            self.say("ERREUR : fichier de traduction manquant (data/all_fr.jsonl). "
                     "Le paquet est incomplet.", "bad")
            self.btn_install.configure(state="disabled")
        self._refresh_status()

    def _browse(self):
        chosen = filedialog.askdirectory(
            title="Choisissez le dossier du jeu (SGRE ou wind3d11data)",
            parent=self)
        if not chosen:
            return
        found = locate.normalize(chosen)
        if not found:
            messagebox.showerror(
                "Dossier incorrect",
                "Ce dossier ne contient pas les fichiers du jeu.\n\n"
                "Cherchez le dossier SGRE (celui qui contient sgre_steam.exe) "
                "ou son sous-dossier wind3d11data.", parent=self)
            return
        self.game_dir.set(found)
        self.say("Dossier choisi : " + found)
        self._refresh_status()

    def _refresh_status(self):
        path = self.game_dir.get()
        if not locate.is_game_dir(path):
            self.status.configure(text="Aucun jeu valide sélectionné.", fg=BAD)
            self.btn_install.configure(state="disabled")
            self.btn_restore.configure(state="disabled")
            return
        self.btn_install.configure(
            state="normal" if os.path.isfile(FR_FILE) else "disabled")
        self.btn_restore.configure(
            state="normal" if patch.has_backup(path) else "disabled")
        state = patch.status(path)
        if state == "installed":
            stamp = patch.read_stamp(path) or {}
            self.status.configure(
                text="Patch FR installé le " + str(stamp.get("installed", "?"))
                     + "  ·  mettez la langue du jeu sur ENGLISH.", fg=OK)
        elif state == "original":
            self.status.configure(
                text="Prêt à installer — aucun patch détecté dans ce dossier.",
                fg=MUTED)
        else:
            self.status.configure(
                text="État inconnu (jeu mis à jour ?). Réinstaller le patch "
                     "corrigera.", fg=ACCENT)

    # ------------------------------------------------------------ background

    def _run(self, fn):
        if self.worker and self.worker.is_alive():
            return
        self._busy(True)
        self.stop_flag = False
        self.progress.configure(value=0)

        def body():
            try:
                fn()
            except patch.Cancelled:
                self.events.put(("done", ("cancel", None)))
            except patch.PatchError as exc:
                self.events.put(("done", ("error", str(exc))))
            except Exception as exc:                      # noqa: BLE001
                self.events.put(("log", (traceback.format_exc(), "bad")))
                self.events.put(("done", ("error",
                                          "Erreur inattendue : " + str(exc))))

        self.worker = threading.Thread(target=body, daemon=True)
        self.worker.start()

    def _pump(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    if isinstance(payload, tuple):
                        self.say(*payload)
                    else:
                        self.say(payload)
                elif kind == "progress":
                    frac, message = payload
                    self.progress.configure(value=int(frac * 1000))
                    self.step.configure(text=message)
                elif kind == "done":
                    self._finish(*payload)
        except queue.Empty:
            pass
        self.after(60, self._pump)

    def _finish(self, outcome, message):
        self._busy(False)
        self._refresh_status()
        if outcome == "installed":
            self.progress.configure(value=1000)
            self.step.configure(text="Terminé.")
            self.say(message, "ok")
            messagebox.showinfo(
                "Patch installé",
                "La traduction française est installée.\n\n"
                "Lancez le jeu et mettez la langue sur ENGLISH : "
                "le texte s'affichera en français.", parent=self)
        elif outcome == "restored":
            self.progress.configure(value=0)
            self.step.configure(text="")
            self.say(message, "ok")
            messagebox.showinfo("Restauration terminée", message, parent=self)
        elif outcome == "cancel":
            self.progress.configure(value=0)
            self.step.configure(text="Annulé.")
            self.say("Annulé — aucun fichier modifié.", "hi")
        else:
            self.progress.configure(value=0)
            self.step.configure(text="Échec.")
            self.say(message, "bad")
            messagebox.showerror("Echec", message, parent=self)

    # --------------------------------------------------------------- actions

    def _install(self):
        game = self.game_dir.get()
        self.say("")
        self.say("Installation dans " + game, "hi")

        def work():
            stats = patch.install(
                game, FR_FILE,
                progress=lambda f, m: self.events.put(("progress", (f, m))),
                should_stop=lambda: self.stop_flag,
                log=lambda m: self.events.put(("log", m)))
            self.events.put(("done", (
                "installed",
                "{} scénarios traduits, {} répliques écrites.".format(
                    stats["patched"], stats["lines"]))))

        self._run(work)

    def _restore(self):
        game = self.game_dir.get()
        if not messagebox.askyesno(
                "Restaurer", "Remettre les fichiers d'origine (texte anglais) ?",
                parent=self):
            return

        def work():
            patch.uninstall(game, log=lambda m: self.events.put(("log", m)))
            self.events.put(("done", ("restored", "Fichiers d'origine restaurés.")))

        self._run(work)


def cli():
    """Headless install/restore, for testing without a display."""
    import argparse
    ap = argparse.ArgumentParser(description="Patch FR STEINS;GATE RE:BOOT")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true")
    group.add_argument("--restore", action="store_true")
    group.add_argument("--status", action="store_true")
    ap.add_argument("--game-dir")
    args = ap.parse_args()

    game = locate.normalize(args.game_dir) if args.game_dir else locate.autodetect()
    if not game:
        sys.exit("jeu introuvable - passez --game-dir")
    print("jeu :", game)
    if args.status:
        print("etat :", patch.status(game))
    elif args.restore:
        patch.uninstall(game, log=print)
        print("restaure.")
    else:
        stats = patch.install(game, FR_FILE,
                              progress=lambda f, m: print("  %5.1f%%  %s" % (f * 100, m)),
                              log=print)
        print(stats)


def main():
    if len(sys.argv) > 1:
        try:
            cli()
        except patch.PatchError as exc:
            sys.exit(str(exc))
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:                                     # noqa: BLE001
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
