import customtkinter as ctk
from generator import generate_npc, Selections
from renderer import RenderedNPC, render_as_text


ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("App")
        self.geometry("1200x800")
        self.top_bar = ctk.CTkFrame(self, height=34, fg_color ="#13110F", corner_radius=0)
        self.rail = ctk.CTkFrame(self, width=48, fg_color="#13110F", corner_radius=0)
        self.panel = ctk.CTkFrame(self, width=240, fg_color="#1F1C1A", corner_radius=0)
        self.preview_well = ctk.CTkFrame(self, fg_color="#0C0C0C", corner_radius=0)
        self.preview_text = ctk.CTkLabel(self.preview_well, font=("Courier New", 13), fg_color="#1F1C1A", text_color="#F6EBE0", justify="left", anchor="nw")

        self.top_bar.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.rail.grid(row=1, column=0, sticky="nsew")
        self.panel.grid(row=1, column=1, sticky="nsew")
        self.preview_well.grid(row=1, column=2, sticky="nsew")
        self.preview_text.grid(row=0, column=1, sticky="nsew", pady=50)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.preview_well.grid_columnconfigure(0, weight=1)
        self.preview_well.grid_columnconfigure(1, weight=0)
        self.preview_well.grid_columnconfigure(2, weight=1)
        self.preview_well.grid_rowconfigure(0, weight=1)

        selection = Selections(cr="5", base="Melee", race="Human")
        rendered = RenderedNPC(generate_npc(selection), name="Test NPC", cr=selection.cr, race=selection.race, personality="Test Personality", alignment="Neutral Good", languages=["Common", "Elvish"])

        self.preview_text.configure(text=render_as_text(rendered))