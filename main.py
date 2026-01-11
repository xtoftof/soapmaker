import flet as ft
import os
import webbrowser
import time
from datetime import datetime
from urllib.parse import quote
from droidmemory import DroidMemory

# Tentative d'import pygame (optionnel pour PC)
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class SoundManager:
    """Gestionnaire audio multi-plateforme"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.mode = "SILENT"
        self.library = {}
        
        # Détection et initialisation du moteur audio
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.mode = "PYGAME"
                print("🎵 Mode audio : Pygame (PC)")
            except Exception as e:
                print(f"⚠️ Pygame init échoué: {e}")
        
        # Liste des fichiers sons
        self.fichiers = {
            "beep": "droid_beep.mp3",
            "save": "droid_save.mp3",
            "beep2": "droid_beep2.mp3",
            "ordre66": "droid_66.mp3",
            "laught": "droid_laught.mp3",
            "dial2": "droid_dial2.mp3",
            "error": "error_sound.mp3",
            "old": "old_droid.mp3",
            "send": "droid_send.mp3",
        }
        
        self._charger_sons()
    
    def _charger_sons(self):
        """Charge les sons selon le moteur disponible"""
        if self.mode == "PYGAME":
            for nom, fichier in self.fichiers.items():
                chemin = f"assets/sounds/{fichier}"
                if os.path.exists(chemin):
                    try:
                        sound = pygame.mixer.Sound(chemin)
                        sound.set_volume(0.7)
                        self.library[nom] = sound
                    except Exception as e:
                        print(f"❌ Erreur chargement {nom}: {e}")
        
        print(f"✅ Sons chargés : {len(self.library)}")
    
    def play(self, nom_cle):
        """Joue un son (si disponible)"""
        if "66" in nom_cle:
            nom_cle = "ordre66"
        
        if self.mode == "PYGAME" and nom_cle in self.library:
            try:
                self.library[nom_cle].play()
            except Exception as e:
                print(f"⚠️ Erreur lecture {nom_cle}: {e}")


class SoapMakerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "SoapMaker - Droid Edition"
        self.page.window.maximized = True
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.AUTO
        
        # Fonts
        self.page.fonts = {
            "staround": "fonts/superrond.ttf",
            "consolas": "fonts/consolas.ttf",
            "droidgift": "fonts/droidgift.ttf"
        }
        self.page.theme = ft.Theme(font_family="consolas")
        
        # Initialisation des données
        self.db_huiles = []
        self.db_additifs = []
        self.db_he = []
        self.sap_values = {}
        self.recette = {}
        
        # Éléments UI
        self.logo = None
        self.entry_nom = None
        self.radio_mode = None
        self.entry_poids_total = None
        self.combo_huiles = None
        self.liste_huiles = None
        self.label_total = None
        
        # Fenêtre 2
        self.lbl_surgras = None
        self.slider_surgras = None
        self.info_surgras = None
        self.lbl_eau = None
        self.slider_eau = None
        self.info_eau = None
        self.combo_sub = None
        self.lbl_pct_sub = None
        self.slider_pct_sub = None
        self.info_sub = None
        self.res_soude = None
        self.res_eau = None
        self.res_sub = None
        self.poids_ref = 0.0
        
        # Services
        self.sound_manager = SoundManager(self.page)
        self.memory = DroidMemory()
        
        # Chargement
        self.charger_toutes_les_bases()
        self.reset_recette_courante()
        
        # Démarrage
        self.afficher_splashscreen()
    
    # ============ SPLASHSCREEN ===============================================
    
    def afficher_splashscreen(self):
        """Affiche le splash avec animation simple"""
        self.page.controls.clear()
        
        self.logo = ft.Image(
            src="logo_titre.png",
            width=320,
            height=320,
            fit=ft.ImageFit.CONTAIN
        )
        
        splash = ft.Container(
            content=ft.Column(
                [self.logo],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            width=400,
            height=700,
            bgcolor=ft.colors.BLACK,
            alignment=ft.alignment.center,
            expand=True
        )
        
        self.page.add(
            ft.Container(
                content=splash,
                expand=True,
                alignment=ft.alignment.center
            )
        )
        self.page.update()
        
        # Animation simple sans async
        time.sleep(2)
        self.afficher_fenetre_1()
    
    # ============ UTILITAIRES ============
    
    def emettre_son(self, fichier):
        """Joue un son"""
        self.sound_manager.play(fichier)
    
    def charger_toutes_les_bases(self):
        """Charge les bases de données JSON"""
        data_huiles = self.memory.charger_json("huiles.json")
        self.db_huiles = data_huiles.get("huiles", []) if isinstance(data_huiles, dict) else []
        self.sap_values = {h["nom"]: h["sap_naoh"] for h in self.db_huiles}
        
        data_additifs = self.memory.charger_json("additifs.json")
        self.db_additifs = data_additifs.get("additifs", []) if isinstance(data_additifs, dict) else []
        
        data_he = self.memory.charger_json("addons_he.json")
        self.db_he = data_he.get("addons_he", []) if isinstance(data_he, dict) else []
    
    def reset_recette_courante(self):
        """Réinitialise la recette"""
        date_jour = datetime.now().strftime("%d/%m/%Y")
        self.recette = {
            "nom_recette": f"Ma Recette du {date_jour}",
            "mode": "Poids",
            "poids_total_desire": 0.0,
            "corps_gras": {},
            "surgras": 5,
            "proportion_eau": 30,
            "substitut_liquide": "Aucun",
            "pourcentage_substitut": 0,
            "additifs": {},
            "he": {}
        }
    
    def obtenir_poids_huiles(self):
        """Retourne le poids total des huiles selon le mode"""
        if self.recette["mode"] == "Poids":
            return float(sum(self.recette["corps_gras"].values()))
        
        cible = float(self.recette["poids_total_desire"])
        taux_eau = self.recette["proportion_eau"] / 100
        return cible / (1 + taux_eau + 0.2)
    
    def afficher_erreur(self, titre, message):
        """Affiche un message d'erreur"""
        snack = ft.SnackBar(
            content=ft.Text(f"{titre}: {message}", size=18),
            bgcolor=ft.colors.RED_700
        )
        self.page.overlay.append(snack)
        snack.open = True
        if not self.page.controls:
            self.page.update()
            return
    
        self.page.update()
    
    def afficher_info(self, titre, message):
        """Affiche un message d'info"""
        snack = ft.SnackBar(
            content=ft.Text(f"{titre}: {message}", size=18, weight=ft.FontWeight.BOLD),
            bgcolor=ft.colors.BLUE_GREY_800
        )
        self.page.overlay.append(snack)
        snack.open = True
        if not self.page.controls:
            self.page.update()
            return
    
        self.page.update()
    
    def fermer_dialog(self, dlg):
        """Ferme un dialogue"""
        self.emettre_son("send")
        dlg.open = False
        self.page.update()
    
    def action_ouvrir_dossier(self, e=None):
        """Ouvre le dossier SaveData"""
        import subprocess
        import platform
        
        sys_name = platform.system()
        try:
            path = str(self.memory.base_dir)
            
            if sys_name == "Windows":
                # Utilise explorer.exe au lieu de startfile pour forcer au premier plan
                subprocess.Popen(f'explorer /select,"{path}"')
            elif sys_name == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as ex:
            self.afficher_erreur("Erreur", f"Impossible d'ouvrir : {ex}")
        
    # ============ FENÊTRE 1 : CORPS GRAS ============
    
    def afficher_fenetre_1(self):
        """Écran de sélection des huiles"""
        self.page.controls.clear()
        self.emettre_son("beep")
        
        header = ft.Container(
            content=ft.Column([
                ft.Text("SoapMaker", size=30, weight=ft.FontWeight.BOLD, font_family="staround"),
                ft.Text("Episode 1 - La Recette Fantome", size=18, font_family="staround"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.colors.BLUE_GREY_900,
            alignment=ft.alignment.center
        )
        
        self.entry_nom = ft.TextField(
            label="Nom de la recette",
            value=self.recette["nom_recette"],
            on_change=lambda e: self.maj_nom_recette(e.control.value)
        )
        
        self.radio_mode = ft.RadioGroup(
            value=self.recette["mode"],
            content=ft.Row([
                ft.Text("Mode : ", size=16),
                ft.Radio(value="Poids", label="Poids (g)"),
                ft.Radio(value="%", label="Pourcentage")
            ], alignment=ft.MainAxisAlignment.CENTER),
            on_change=lambda e: self.changer_mode(e.control.value)
        )
        
        self.entry_poids_total = ft.TextField(
            label="Poids TOTAL désiré (g)",
            value=str(self.recette["poids_total_desire"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=200,
            visible=(self.recette["mode"] == "%"),
            on_change=lambda e: self.sauver_poids_total(e.control.value)
        )
        
        self.combo_huiles = ft.Dropdown(
            label="Choisir une huile",
            options=[ft.dropdown.Option(h["nom"]) for h in self.db_huiles],
            expand=True
        )
        
        btn_add = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE,
            icon_color=ft.colors.GREEN,
            icon_size=40,
            on_click=lambda e: self.ajouter_huile()
        )
        
        self.liste_huiles = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
        self.label_total = ft.Text("Total : 0 g", size=18, weight=ft.FontWeight.BOLD)
        
        self.rafraichir_liste_huiles()
        
        btn_droid = ft.Container(
            content=ft.Row([
                ft.Image(
                    src="Droid_line.png",
                    width=25,
                    height=25,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Text("DROID ASSISTANT", size=14, weight=ft.FontWeight.BOLD)
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            padding=10,
            bgcolor=ft.colors.BLUE_700,
            border_radius=5,
            ink=True,  # Effet de clic
            on_click=lambda e: self.afficher_droid_assistant()
        )
        
        btn_suivant = ft.FilledButton(
            "SUIVANT →",
            icon=ft.icons.ARROW_FORWARD,
            on_click=lambda e: self.valider_fenetre_1(),
            style=ft.ButtonStyle(bgcolor=ft.colors.ORANGE)
        )
        
        self.page.add(
            ft.Column([
                header,
                ft.Container(
                    content=ft.Column([
                        self.entry_nom,
                        self.radio_mode,
                        self.entry_poids_total,
                        ft.Divider(),
                        ft.Row([self.combo_huiles, btn_add]),
                        self.liste_huiles,
                        self.label_total,
                    ], spacing=10, scroll=ft.ScrollMode.AUTO),
                    padding=15,
                    expand=True
                ),
                ft.Container(
                    content=ft.Row([btn_droid, btn_suivant], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            ], spacing=0, expand=True)
        )
        
        self.page.update()
    
    def changer_mode(self, mode):
        """Change le mode de calcul"""
        self.recette["mode"] = mode
        self.afficher_fenetre_1()
    
    def maj_nom_recette(self, val):
        """Met à jour le nom de la recette"""
        self.recette["nom_recette"] = val.strip() if val.strip() else self.recette["nom_recette"]
    
    def sauver_poids_total(self, val):
        """Sauvegarde le poids total"""
        try:
            self.recette["poids_total_desire"] = float(val.replace(",", "."))
        except (ValueError, AttributeError):
            pass
    
    def ajouter_huile(self):
        """Ajoute une huile à la recette"""
        nom = self.combo_huiles.value
        if not nom:
            return
        
        if nom in self.recette["corps_gras"]:
            self.afficher_info("Déjà présent", f"'{nom}' est déjà dans la liste.")
            return
        
        self.recette["corps_gras"][nom] = 0
        self.rafraichir_liste_huiles()
    
    def rafraichir_liste_huiles(self):
        """Rafraîchit l'affichage des huiles"""
        self.liste_huiles.controls.clear()
        
        for nom, val in self.recette["corps_gras"].items():
            info = next((h for h in self.db_huiles if h["nom"] == nom), {})
            
            ligne = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(nom, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(info.get("qualite", "-"), size=12, color=ft.colors.GREY),
                        ft.Text(
                            f"Mousse: {info.get('mousse', '-')} | {info.get('recommande', 'N/A')}",
                            size=11,
                            italic=True
                        )
                    ], spacing=2, expand=True),
                    ft.TextField(
                        value=str(val),
                        width=70,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        text_align=ft.TextAlign.CENTER,
                        on_change=lambda e, n=nom: self.maj_valeur_huile(n, e.control.value)
                    ),
                    ft.Text("g" if self.recette["mode"] == "Poids" else "%", width=20),
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color=ft.colors.RED,
                        icon_size=20,
                        on_click=lambda e, n=nom: self.supprimer_huile(n)
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=8,
                border=ft.border.all(1, ft.colors.GREY_700),
                border_radius=5
            )
            
            self.liste_huiles.controls.append(ligne)
        
        self.maj_total()
        self.page.update()
    
    def maj_valeur_huile(self, nom, val_str):
        """Met à jour la valeur d'une huile"""
        try:
            val = 0.0 if val_str in ["", "-", "."] else float(val_str.replace(",", "."))
            self.recette["corps_gras"][nom] = val
            self.maj_total()
        except (ValueError, AttributeError):
            pass
    
    def supprimer_huile(self, nom):
        """Supprime une huile"""
        del self.recette["corps_gras"][nom]
        self.rafraichir_liste_huiles()
    
    def maj_total(self):
        """Met à jour le total"""
        total = sum(self.recette["corps_gras"].values())
        unite = "g" if self.recette["mode"] == "Poids" else "%"
        self.label_total.value = f"Total : {round(total, 2)} {unite}"
        
        if self.recette["mode"] == "%":
            self.label_total.color = ft.colors.GREEN if abs(total - 100) < 0.01 else ft.colors.ORANGE
        
        self.page.update()
    
    def valider_fenetre_1(self):
        """Valide la fenêtre 1"""
        cg = self.recette["corps_gras"]
        
        if not cg:
            self.afficher_erreur("Erreur", "Sans huiles, un savon n'est pas.")
            self.emettre_son("error")
            return
        
        for nom, val in cg.items():
            if val <= 0:
                self.afficher_erreur("Valeur manquante", f"Donner une valeur à '{nom}' tu dois !")
                self.emettre_son("error")
                return
        
        if self.recette["mode"] == "%":
            try:
                poids = float(self.entry_poids_total.value.replace(",", "."))
                if poids <= 10:
                    raise ValueError
                self.recette["poids_total_desire"] = poids
            except (ValueError, AttributeError):
                self.afficher_erreur("Erreur", "Un poids total valide il te manque.")
                self.emettre_son("error")
                return
            
            total = sum(cg.values())
            if abs(total - 100) > 0.01:
                self.afficher_erreur("Calcul incorrect", f"100% tu dois atteindre. Actuellement : {total}%")
                self.emettre_son("laught")
                return
        else:
            if sum(cg.values()) <= 0:
                self.afficher_erreur("Erreur", "Un poids total supérieur à zéro il faut.")
                self.emettre_son("error")
                return
        
        self.afficher_fenetre_2()
    
    # ============ FENÊTRE 2 : LESSIVE ============
    
    def afficher_fenetre_2(self):
        """Écran de configuration de la lessive"""
        self.page.controls.clear()
        self.emettre_son("beep2")
        
        header = ft.Container(
            content=ft.Column([
                ft.Text("SoapMaker", size=30, weight=ft.FontWeight.BOLD, font_family="staround"),
                ft.Text("Episode 2 - L'Eveil de la Soude", size=18, font_family="staround"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.colors.BLUE_GREY_900,
            alignment=ft.alignment.center
        )
        
        # Surgraissage
        self.lbl_surgras = ft.Text(f"Surgraissage : {self.recette['surgras']}%", weight=ft.FontWeight.BOLD)
        self.slider_surgras = ft.Slider(
            min=0,
            max=15,
            divisions=15,
            value=self.recette["surgras"],
            on_change=lambda e: self.maj_surgras(int(e.control.value))
        )
        self.info_surgras = ft.Text("", size=13, italic=True, color=ft.colors.GREY)
        
        # Eau
        self.lbl_eau = ft.Text(f"Proportion liquide : {self.recette['proportion_eau']}%", weight=ft.FontWeight.BOLD)
        self.slider_eau = ft.Slider(
            min=25,
            max=40,
            divisions=15,
            value=self.recette["proportion_eau"],
            on_change=lambda e: self.maj_eau(int(e.control.value))
        )
        self.info_eau = ft.Text("", size=13, italic=True, color=ft.colors.GREY)
        
        # Substitut
        liquides = ["Aucun"] + [a["Additif"] for a in self.db_additifs if a.get("Cat") == "Liquide"]
        
        self.combo_sub = ft.Dropdown(
            label="Substitution eau",
            options=[ft.dropdown.Option(l) for l in liquides],
            value=self.recette.get("substitut_liquide", "Aucun"),
            on_change=lambda e: self.maj_lessive()
        )
        
        self.lbl_pct_sub = ft.Text(
            f"% de substitution : {self.recette['pourcentage_substitut']}%",
            weight=ft.FontWeight.BOLD
        )
        self.slider_pct_sub = ft.Slider(
            min=0,
            max=100,
            divisions=20,
            value=self.recette.get("pourcentage_substitut", 0),
            on_change=lambda e: self.maj_slider_pct(int(e.control.value))
        )
        self.info_sub = ft.Text("", size=11, italic=True, color=ft.colors.CYAN)
        
        # Résultats
        self.res_soude = ft.Text("Soude (NaOH) : ...", weight=ft.FontWeight.BOLD)
        self.res_eau = ft.Text("Eau Distillée : ...", weight=ft.FontWeight.BOLD)
        self.res_sub = ft.Text("Additif-substitut : ...", color=ft.colors.ORANGE, weight=ft.FontWeight.BOLD)
        
        result_box = ft.Container(
            content=ft.Column([
                ft.Text("Composition phase liquide", size=18, weight=ft.FontWeight.BOLD),
                self.res_soude,
                self.res_eau,
                self.res_sub
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.colors.BLUE_GREY,
            alignment=ft.alignment.center,
            border_radius=10
        )
        
        btn_retour = ft.FilledButton("← RETOUR", on_click=lambda e: self.afficher_fenetre_1())
        btn_suivant = ft.FilledButton(
            "EPISODE 3 →",
            on_click=lambda e: self.valider_fenetre_2(),
            style=ft.ButtonStyle(bgcolor=ft.colors.ORANGE)
        )
        
        self.page.add(
            ft.Column([
                header,
                ft.Container(
                    content=ft.Column([
                        self.lbl_surgras, self.slider_surgras, self.info_surgras,
                        ft.Divider(height=20),
                        self.lbl_eau, self.slider_eau, self.info_eau,
                        ft.Divider(height=20),
                        self.combo_sub,
                        self.lbl_pct_sub,
                        self.slider_pct_sub,
                        self.info_sub,
                        ft.Divider(height=20),
                        result_box
                    ], scroll=ft.ScrollMode.AUTO, spacing=10),
                    padding=15,
                    expand=True
                ),
                ft.Container(
                    content=ft.Row([btn_retour, btn_suivant], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            ], spacing=0, expand=True)
        )
        
        self.maj_surgras(self.recette["surgras"])
        self.maj_eau(self.recette["proportion_eau"])
        self.maj_lessive()
        self.page.update()
    
    def maj_surgras(self, v):
        """Met à jour le surgraissage"""
        self.recette["surgras"] = v
        self.lbl_surgras.value = f"Surgraissage : {v}%"
        
        if v <= 2:
            msg = "Très bas ! Bon pour SAC."
        elif v <= 4:
            msg = "Bas, surgraissage à la trace recommandé."
        elif v <= 8:
            msg = "Idéal pour toute recette."
        elif v <= 13:
            msg = "Élevé, attention au rejet."
        else:
            msg = "Très élevé, vérifier la recette !"
        
        self.info_surgras.value = msg
        self.maj_lessive()
        self.page.update()
    
    def maj_eau(self, v):
        """Met à jour la proportion d'eau"""
        self.recette["proportion_eau"] = v
        self.lbl_eau.value = f"Proportion liquide : {v}%"
        
        if v <= 28:
            msg = "Bas, prise rapide."
        elif v <= 33:
            msg = "Moyen, polyvalent."
        elif v <= 36:
            msg = "Élevé, bon pour marbrages."
        else:
            msg = "Très élevé (SAC ou lait)."
        
        self.info_eau.value = msg
        self.maj_lessive()
        self.page.update()
    
    def maj_slider_pct(self, v):
        """Met à jour le pourcentage de substitution"""
        self.recette["pourcentage_substitut"] = v
        self.lbl_pct_sub.value = f"% de substitution : {v}%"
        self.maj_lessive()
        self.page.update()
    
    def maj_lessive(self):
        """Calcule la composition de la lessive"""
        sub = self.combo_sub.value if self.combo_sub.value else "Aucun"
        pct = self.recette["pourcentage_substitut"]
        self.recette["substitut_liquide"] = sub
        
        if sub == "Aucun":
            self.recette["pourcentage_substitut"] = 0
            self.slider_pct_sub.value = 0
            self.lbl_pct_sub.value = "% de substitution : 0%"
        
        ph = self.obtenir_poids_huiles()
        
        naoh = 0
        for nom, val in self.recette["corps_gras"].items():
            poids_h = val if self.recette["mode"] == "Poids" else (val/100) * ph
            sap = next((h["sap_naoh"] for h in self.db_huiles if h["nom"] == nom), 0.135)
            naoh += poids_h * sap
        
        naoh *= (1 - self.recette["surgras"]/100)
        
        liq_total = ph * (self.recette["proportion_eau"]/100)
        liq_sub = liq_total * (pct/100)
        liq_eau = liq_total - liq_sub
        
        self.res_soude.value = f"Soude (NaOH) : {round(naoh, 1)} g"
        self.res_eau.value = f"Eau : {round(liq_eau, 1)} g"
        self.res_sub.value = f"{sub} : {round(liq_sub, 1)} g" if sub != "Aucun" and pct > 0 else ""
        self.res_sub.visible = True if (sub != "Aucun" and pct > 0) else False
        
        item = next((a for a in self.db_additifs if a["Additif"] == sub), None)
        self.info_sub.value = f"{item.get('Propriété', '')} (Reco: {item.get('% conseillé', '')})" if item else ""
        
        self.page.update()
    
    def valider_fenetre_2(self):
        """Valide la fenêtre 2"""
        sub = self.combo_sub.value
        pct = self.recette["pourcentage_substitut"]
        
        if sub != "Aucun" and pct == 0:
            self.afficher_erreur("Oubli", "Un pourcentage pour ton substitut, choisir tu dois !")
            self.emettre_son("error")
            return
        
        if sub == "Aucun" and pct > 0:
            self.afficher_erreur("Erreur", "Quel liquide veux-tu ? Un nom choisis, ou à 0% remets !")
            self.emettre_son("laught")
            return
        
        self.afficher_fenetre_3()
    
    # ============ FENÊTRE 3 : ADDITIFS ============
    
    def afficher_fenetre_3(self):
        """Écran des additifs et huiles essentielles"""
        self.page.controls.clear()
        self.emettre_son("dial2")
        
        header = ft.Container(
            content=ft.Column([
                ft.Text("SoapMaker", size=30, weight=ft.FontWeight.BOLD, font_family="staround"),
                ft.Text("Episode 3 - Le Retour de la Trace", size=18, font_family="staround"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.colors.BLUE_GREY_900,
            alignment=ft.alignment.center
        )
        
        self.poids_ref = self.obtenir_poids_huiles()
        
        # Cartouches
        additifs_list = [a["Additif"] for a in self.db_additifs if "Cosmétiques" not in a.get("Additif", "")]
        cart_additifs = self.creer_cartouche(
            titre="Additifs (Argiles, Poudres)",
            items=additifs_list,
            dico="additifs",
            limite=10,
            bg=ft.colors.BROWN_100,
            est_he=False
        )
        
        he_list = [h["Nom"] for h in self.db_he]
        cart_he = self.creer_cartouche(
            titre="Huiles Essentielles",
            items=he_list,
            dico="he",
            limite=3,
            bg=ft.colors.PINK_100,
            est_he=True
        )
        
        btn_retour = ft.FilledButton("← RETOUR", on_click=lambda e: self.afficher_fenetre_2())
        btn_calc = ft.FilledButton(
            "CALCULER →",
            on_click=lambda e: self.valider_fenetre_3(),
            style=ft.ButtonStyle(bgcolor=ft.colors.GREEN)
        )
        
        self.page.add(
            ft.Column([
                header,
                ft.Container(
                    content=ft.Column([cart_additifs, cart_he], scroll=ft.ScrollMode.AUTO, spacing=15),
                    padding=15,
                    expand=True
                ),
                ft.Container(
                    content=ft.Row([btn_retour, btn_calc], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=15
                )
            ], spacing=0, expand=True)
        )
        
        self.page.update()
    
    def creer_cartouche(self, titre, items, dico, limite, bg, est_he):
        """Crée un bloc Additif ou HE"""
        combo = ft.Dropdown(
            label="Choisir",
            label_style=ft.TextStyle(color=ft.colors.BLACK),
            text_style=ft.TextStyle(color=ft.colors.BLACK),
            bgcolor=ft.colors.WHITE,  # ✅ Ajoute un fond blanc au dropdown
            options=[ft.dropdown.Option(i) for i in sorted(items)],
            expand=True
        )
        
        liste = ft.Column(spacing=5)
        total_lbl = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        
        btn_add = ft.IconButton(
            icon=ft.icons.ADD_CIRCLE,
            icon_color=ft.colors.GREEN,
            on_click=lambda e: self.ajouter_item(dico, combo.value, liste, total_lbl, limite, est_he)
        )
        
        if est_he:
            legende = ft.Text(
                "Tox UV : ++ Fort | + Présent | 0 Inconnu | E: Éviter pour maternité",
                size=12,
                italic=True,
                color=ft.colors.BLACK
            )
        else:
            legende = None
        
        self.maj_total_items(dico, total_lbl, limite)
        self.rafraichir_items(dico, liste, total_lbl, limite, est_he)
        
        controls = [
            ft.Text(titre, size=15, weight=ft.FontWeight.BOLD, color=ft.colors.BLACK),
            ft.Row([combo, btn_add]),
            liste,
            total_lbl
        ]
        
        if legende:
            controls.append(legende)
        
        return ft.Container(
            content=ft.Column(controls, spacing=8),
            padding=12,
            bgcolor=bg,
            border_radius=8
        )
    
    def ajouter_item(self, dico, nom, liste_widget, total_lbl, limite, est_he):
        """Ajoute un additif/HE"""
        if not nom:
            return
        
        if nom not in self.recette[dico]:
            self.recette[dico][nom] = 0.0
            self.rafraichir_items(dico, liste_widget, total_lbl, limite, est_he)
    
    def rafraichir_items(self, dico, liste_widget, total_lbl, limite, est_he):
        """Rafraîchit liste additifs/HE"""
        liste_widget.controls.clear()
        
        for nom, poids in self.recette[dico].items():
            if est_he:
                data = next((h for h in self.db_he if h["Nom"] == nom), {})
                prop = data.get("Propriétés", "-")
                tox = data.get("Toxicité", "0")
                info_txt = f"{prop} (Tox: {tox})"
                
                if "++" in tox:
                    txt_color = ft.colors.RED_700
                elif "+" in tox:
                    txt_color = ft.colors.ORANGE_700
                else:
                    txt_color = ft.colors.GREY_700
            else:
                data = next((a for a in self.db_additifs if a["Additif"] == nom), {})
                info_txt = data.get("Propriété", "-")
                txt_color = ft.colors.BLACK
            
            ligne = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(nom, color=ft.colors.BLACK, weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(info_txt, size=12, color=txt_color)
                    ], spacing=2, expand=True),
                    ft.TextField(
                        value=str(poids),
                        width=60,
                        keyboard_type=ft.KeyboardType.NUMBER,
                        text_style=ft.TextStyle(color=ft.colors.BLACK),
                        text_align=ft.TextAlign.CENTER,
                        on_change=lambda e, n=nom, d=dico, t=total_lbl, l=limite:
                            self.maj_item(n, e.control.value, d, t, l)
                    ),
                    ft.Text("g", color=ft.colors.BLACK, width=20),
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        icon_color=ft.colors.RED,
                        icon_size=18,
                        on_click=lambda e, n=nom, d=dico, lw=liste_widget, t=total_lbl, l=limite, h=est_he:
                            self.supprimer_item(n, d, lw, t, l, h)
                    )
                ]),
                padding=6,
                border=ft.border.all(1, ft.colors.GREY_600),
                border_radius=5
            )
            
            liste_widget.controls.append(ligne)
        
        self.page.update()
    
    def maj_item(self, nom, val_str, dico, total_lbl, limite):
        """Met à jour un item"""
        try:
            val = 0.0 if val_str in ["", "-", "."] else float(val_str.replace(",", "."))
            self.recette[dico][nom] = val
            self.maj_total_items(dico, total_lbl, limite)
        except (ValueError, AttributeError):
            pass
    
    def supprimer_item(self, nom, dico, liste_widget, total_lbl, limite, est_he):
        """Supprime un item"""
        del self.recette[dico][nom]
        self.rafraichir_items(dico, liste_widget, total_lbl, limite, est_he)
    
    def maj_total_items(self, dico, total_lbl, limite):
        """Met à jour le total des additifs/HE"""
        total = sum(self.recette[dico].values())
        pct = (total / self.poids_ref * 100) if self.poids_ref > 0 else 0
        max_g = self.poids_ref * (limite / 100)
        
        texte = f"Total : {round(total, 1)} g ({round(pct, 1)}%)\nMax conseillé : {round(max_g, 1)} g ({limite}%)"
        
        if pct > limite:
            total_lbl.value = texte + " ⚠️ TROP ÉLEVÉ"
            total_lbl.color = ft.colors.RED
        else:
            total_lbl.value = texte
            total_lbl.color = ft.colors.GREEN
        
        self.page.update()
    
    def valider_fenetre_3(self):
        """Valide la fenêtre 3"""
        erreurs = []
        
        for nom, poids in self.recette["additifs"].items():
            if poids <= 0:
                erreurs.append(f"Additif '{nom}'")
        
        for nom, poids in self.recette["he"].items():
            if poids <= 0:
                erreurs.append(f"HE '{nom}'")
        
        if erreurs:
            self.afficher_erreur("Valeurs manquantes", "Certains items sont à 0 :\n" + "\n".join(erreurs))
            self.emettre_son("laught")
            return
        
        self.afficher_info("You're clear!", "Now let's cook this soap and go home!")
        self.afficher_fenetre_4()
    
    # ============ FENÊTRE 4 : RÉSULTATS ============
    
    def afficher_fenetre_4(self):
        """Écran des résultats"""
        self.page.controls.clear()
        self.emettre_son("save")
        
        date = datetime.now().strftime("%d/%m/%Y")
        header = ft.Container(
            content=ft.Column([
                ft.Text("SoapMaker", size=28, weight=ft.FontWeight.BOLD, font_family="staround"),
                ft.Text(f"Episode 4 - L'Etoile du {date}", size=16, font_family="staround"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=15,
            bgcolor=ft.colors.BLUE_GREY_900,
            alignment=ft.alignment.center
        )
        
        res = self.calculer_chimie_recette(self.recette)
        
        if not res:
            self.afficher_erreur("Erreur", "Impossible de calculer la recette.")
            return
        
        resume = self.generer_resume_texte(res)
        
        txt_resume = ft.Text(
            value=resume,
            size=18,
            font_family="droidgift",
            text_align=ft.TextAlign.CENTER,
            color=ft.colors.GREEN_400,
            weight=ft.FontWeight.W_500
        )
        
        zone_centrale = ft.Container(
            content=txt_resume,
            alignment=ft.alignment.center,
            expand=True,
            padding=20,
            bgcolor=ft.colors.BLACK12,
            border_radius=10
        )
        
        btn_retour = ft.FilledButton("← RETOUR", on_click=lambda e: self.afficher_fenetre_3())
        btn_droid = ft.Container(
            content=ft.Row([
                ft.Image(
                    src="Droid_line.png",
                    width=25,
                    height=25,
                    fit=ft.ImageFit.CONTAIN,
                ),
                ft.Text("DROID ASSISTANT", size=14, weight=ft.FontWeight.BOLD)
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            padding=10,
            bgcolor=ft.colors.BLUE_700,
            border_radius=5,
            ink=True,  # Effet de clic
            on_click=lambda e: self.afficher_droid_assistant()
        )
        btn_reset = ft.FilledButton(
            "RECOMMENCER",
            icon=ft.icons.REFRESH,
            on_click=lambda e: self.reset_app(),
            style=ft.ButtonStyle(bgcolor=ft.colors.RED_700)
        )
        btn_save = ft.FilledButton(
            "ARCHIVER",
            icon=ft.icons.SAVE,
            on_click=self.action_sauvegarder_finale,
            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_700)
        )
        
        actions_row = ft.Row([
            btn_reset,
            btn_save
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        actions_row_2 = ft.Row([
            btn_retour,
            btn_droid
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        self.page.add(
            ft.Column([
                header,
                ft.Container(content=zone_centrale, padding=10, expand=True),
                ft.Container(content=actions_row, padding=15),
                ft.Container(content=actions_row_2, padding=15)
            ], expand=True)
        )
        self.page.update()
    
    def calculer_chimie_recette(self, data):
        """Moteur de calcul chimique"""
        cg = data.get("corps_gras", {})
        ph = self.obtenir_poids_huiles()
        
        if ph == 0:
            return None
        
        # Détermination poids par huile
        if data.get("mode") == "Poids":
            detail_g = cg.copy()
        else:
            detail_g = {nom: (pct/100) * ph for nom, pct in cg.items()}
        
        # Calcul soude
        naoh = 0
        for nom, poids in detail_g.items():
            sap = self.sap_values.get(nom, 0.135)
            naoh += poids * sap
        
        surgras = float(data.get("surgras", 5))
        naoh_final = naoh * (1 - surgras/100)
        
        # Liquides
        conc_eau = float(data.get("proportion_eau", 30))
        liq_total = ph * (conc_eau / 100)
        
        sub_nom = data.get("substitut_liquide", "Aucun")
        pct_sub = float(data.get("pourcentage_substitut", 0))
        liq_sub = liq_total * (pct_sub / 100) if sub_nom != "Aucun" else 0
        liq_eau = liq_total - liq_sub
        
        # Ajouts
        total_add = sum(data.get("additifs", {}).values())
        total_he = sum(data.get("he", {}).values())
        
        # Totaux
        pate_fraiche = ph + naoh_final + liq_total + total_add + total_he
        apres_cure = pate_fraiche - (liq_total * 0.4)
        volume = pate_fraiche * 0.95
        
        return {
            "poids_huiles": ph,
            "detail_huiles_g": detail_g,
            "poids_soude": naoh_final,
            "poids_liquide_total": liq_total,
            "poids_eau": liq_eau,
            "poids_substitut": liq_sub,
            "total_frais": pate_fraiche,
            "total_cure": apres_cure,
            "volume": volume
        }
    
    def generer_resume_texte(self, res):
        """Génère le texte du résumé"""
        lignes = [
            f"FICHE : {self.recette['nom_recette']}",
            "=" * 50,
            f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Surgras : {self.recette['surgras']}% | Eau : {self.recette['proportion_eau']}%",
            "-" * 50,
            "",
            f"[1] PHASE GRASSE ({res['poids_huiles']:.1f} g)"
        ]
        
        for nom, poids in res['detail_huiles_g'].items():
            lignes.append(f"  • {nom} : {poids:.1f} g")
        lignes.append("")
        
        lignes.append("[2] SOLUTION DE SOUDE (DANGER)")
        lignes.append(f"  • NaOH : {res['poids_soude']:.2f} g")
        lignes.append(f"  • Eau : {res['poids_eau']:.1f} g")
        if res['poids_substitut'] > 0:
            lignes.append(f"  • {self.recette['substitut_liquide']} : {res['poids_substitut']:.1f} g")
        lignes.append("")
        
        lignes.append("[3] AJOUTS À LA TRACE")

        # Vérifier s'il y a des ajouts
        a_des_additifs = bool(self.recette["additifs"])
        a_des_he = bool(self.recette["he"])

        if not a_des_additifs and not a_des_he:
            lignes.append("  • Rien")
        else:
            if self.recette["additifs"]:
                for nom, val in self.recette["additifs"].items():
                    lignes.append(f"  • {nom} : {val} g")
            if self.recette["he"]:
                for nom, val in self.recette["he"].items():
                    lignes.append(f"  • HE {nom} : {val} g")

        lignes.append("")
        
        lignes.append("=" * 50)
        lignes.append(f"POIDS PÂTE FRAÎCHE : {res['total_frais']:.1f} g")
        lignes.append(f"APRÈS CURE (4-6 sem) : ~{res['total_cure']:.1f} g")
        lignes.append(f"VOLUME MOULE : ~{res['volume']:.0f} ml")
        lignes.append("-" * 50)
        lignes.append("Généré par SoapMaker Droid Edition")
        
        return "\n".join(lignes)
    
    def reset_app(self):
        """Réinitialise l'application"""
        def confirmer(e):
            self.emettre_son("ordre66")
            dlg.open = False
            self.page.update()
            
            self.reset_recette_courante()
            self.afficher_fenetre_1()
        
        dlg = ft.AlertDialog(
            title=ft.Text("☠️ Ordre 66"),
            content=ft.Text("Tout effacer et recommencer ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e: self.fermer_dialog(dlg)),
                ft.TextButton("OUI, TOUT EFFACER", on_click=confirmer, style=ft.ButtonStyle(color=ft.colors.RED))
            ]
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
    
    # ============ FENÊTRE 5 : DROID ASSISTANT ============
    
    def afficher_droid_assistant(self):
        """Écran de gestion des recettes"""

        self.page.controls.clear()
        self.emettre_son("dial2")
        
        fichiers = self.memory.lister_recettes()
        
        if not fichiers:
            content_memoire = ft.Text("Mémoire vide...", italic=True, color=ft.colors.GREY)
        else:
            content_memoire = ft.RadioGroup(
                content=ft.Column(
                    [ft.Radio(value=f, label=f) for f in fichiers],
                    scroll=ft.ScrollMode.AUTO
                ),
                value=None
            )

        def verifier_selection():
            if not isinstance(content_memoire, ft.RadioGroup) or not content_memoire.value:
                self.afficher_erreur("Oups", "Sélectionne une recette d'abord !")
                self.emettre_son("error")
                return None
            return content_memoire.value
        
        def action_charger(e):
            fichier = verifier_selection()
            if fichier:
                self.recette = self.memory.charger_json(fichier)
                self.afficher_info("Droid", "Mémoire restaurée avec succès !")
                self.afficher_fenetre_4()
        
        def action_supprimer(e):
            fichier = verifier_selection()
            if fichier:
                self.memory.supprimer_recette(fichier)
                self.afficher_info("Nettoyage", "Fichier supprimé.")
                self.afficher_droid_assistant()
        
        def action_renommer(e):
            fichier = verifier_selection()
            if not fichier:
                return
            
            tf_rename = ft.TextField(label="Nouveau nom", value=fichier.replace(".json", ""))
            
            def valider_rename(ev):
                if tf_rename.value:
                    self.memory.renommer_recette(fichier, tf_rename.value)
                    dlg_rename.open = False
                    self.page.update()
                    self.afficher_droid_assistant()
            
            dlg_rename = ft.AlertDialog(
                title=ft.Text("Renommer"),
                content=tf_rename,
                actions=[
                    ft.TextButton("Annuler", on_click=lambda ev: self.fermer_dialog(dlg_rename)),
                    ft.TextButton("Valider", on_click=valider_rename)
                ]
            )
            self.page.overlay.append(dlg_rename)
            dlg_rename.open = True
            self.page.update()
        
        def action_exporter(e):
            fichier = verifier_selection()
            if not fichier:
                return
            
            recette_a_exporter = self.memory.charger_json(fichier)
            
            def export_pdf(ev):
                try:
                    chemin = self.memory.generer_pdf_recette(recette_a_exporter)
                    dlg_export.open = False
                    self.page.update()
                    self.afficher_info("PDF Généré", f"Fichier sauvegardé :\n{chemin}")
                    self.emettre_son("old")
                except Exception as ex:
                    dlg_export.open = False
                    self.page.update()
                    self.afficher_erreur("Erreur PDF", str(ex))
                    self.emettre_son("error")
            
            def export_mail(ev):
                try:
                    texte = self.memory.generer_texte_mail(recette_a_exporter)
                    nom = recette_a_exporter.get("nom_recette", "Recette")
                    
                    sujet = quote(f"Recette Savon : {nom}")
                    corps = quote(texte)
                    
                    webbrowser.open(f"mailto:?subject={sujet}&body={corps}")
                    
                    dlg_export.open = False
                    self.page.update()
                    self.afficher_info("Mail", "Client mail ouvert !")
                    self.emettre_son("send")
                except Exception as ex:
                    dlg_export.open = False
                    self.page.update()
                    self.afficher_erreur("Erreur Mail", str(ex))
                    self.emettre_son("error")
            
            dlg_export = ft.AlertDialog(
                title=ft.Text("📤 Options d'Exportation"),
                content=ft.Text(f"Choisir le format pour {fichier}"),
                actions=[
                    ft.FilledButton("PDF", icon=ft.icons.PICTURE_AS_PDF, on_click=export_pdf),
                    ft.FilledButton("Mail", icon=ft.icons.EMAIL, on_click=export_mail),
                    ft.TextButton("Annuler", on_click=lambda ev: self.fermer_dialog(dlg_export))
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
            )
            
            self.page.overlay.append(dlg_export)
            dlg_export.open = True
            self.page.update()
        
        # Champs ajout ressource
        t_nom = ft.TextField(label="Nom", border_color=ft.colors.ORANGE, expand=True)
        t_reco = ft.TextField(label="% Recommandé (ex: 5-15%)", text_size=12, width=150)
        t_prop = ft.TextField(label="Propriétés / Notes", multiline=True, min_lines=2)
        
        t_sap = ft.TextField(label="SAP NaOH (ex: 0.135)", visible=True, width=150)
        t_mousse = ft.TextField(label="Qualité Mousse (ex: Riche)", visible=True, expand=True)
        
        d_type_additif = ft.Dropdown(
            label="Type",
            options=[ft.dropdown.Option("Liquide"), ft.dropdown.Option("Trace (Poudre/Argile)")],
            visible=False,
            width=200
        )
        
        d_tox_he = ft.Dropdown(
            label="Toxicité",
            options=[
                ft.dropdown.Option("0", "Nulle (0)"),
                ft.dropdown.Option("+", "Faible (+)"),
                ft.dropdown.Option("++", "Moyenne (++)"),
                ft.dropdown.Option("E", "Contre-indiqué Maternité (E)")
            ],
            visible=False,
            width=200
        )
        
        def maj_champs(e):
            val = e.control.value
            t_sap.visible = False
            t_mousse.visible = False
            d_type_additif.visible = False
            d_tox_he.visible = False
            t_reco.visible = True
            
            if val == "Huile":
                t_sap.visible = True
                t_mousse.visible = True
            elif val == "Additif":
                d_type_additif.visible = True
            elif val == "HE":
                d_tox_he.visible = True
                t_reco.visible = False
            
            self.page.update()
        
        radio_type = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Huile", label="Corps Gras"),
                ft.Radio(value="Additif", label="Additif"),
                ft.Radio(value="HE", label="H. Essentielle"),
            ], alignment=ft.MainAxisAlignment.CENTER),
            value="Huile",
            on_change=maj_champs
        )
        
        def action_sauvegarder_ressource(e):
            self.emettre_son("save")
            nom_res = t_nom.value.strip()
            mode_res = radio_type.value
            
            if not nom_res:
                return self.afficher_erreur("Erreur", "Le nom est obligatoire.")
            
            try:
                if mode_res == "Huile":
                    try:
                        sap = float(t_sap.value.replace(",", "."))
                    except (ValueError, AttributeError):
                        return self.afficher_erreur("Erreur", "SAP invalide (doit être un chiffre).")
                    
                    new_item = {
                        "nom": nom_res,
                        "sap_naoh": sap,
                        "qualite": t_prop.value,
                        "mousse": t_mousse.value,
                        "recommande": t_reco.value
                    }
                    self.db_huiles.append(new_item)
                    self.memory.sauvegarder_ressource("huiles.json", {"huiles": self.db_huiles})
                    self.charger_toutes_les_bases()
                
                elif mode_res == "Additif":
                    cat = d_type_additif.value if d_type_additif.value else "Trace"
                    new_item = {
                        "Additif": nom_res,
                        "Propriété": t_prop.value,
                        "% conseillé": t_reco.value,
                        "Cat": cat
                    }
                    self.db_additifs.append(new_item)
                    self.memory.sauvegarder_ressource("additifs.json", {"additifs": self.db_additifs})
                    self.charger_toutes_les_bases()
                
                elif mode_res == "HE":
                    tox = d_tox_he.value if d_tox_he.value else "0"
                    new_item = {
                        "Nom": nom_res,
                        "Propriétés": t_prop.value,
                        "Toxicité": tox
                    }
                    self.db_he.append(new_item)
                    self.memory.sauvegarder_ressource("addons_he.json", {"addons_he": self.db_he})
                    self.charger_toutes_les_bases()
                
                self.afficher_info("Succès", f"{nom_res} a été intégré à la base !")
                t_nom.value = ""
                t_prop.value = ""
                self.page.update()
            
            except Exception as ex:
                self.afficher_erreur("Bug Système", str(ex))
        
        # Assemblage visuel
        self.page.add(
            ft.Container(
                content=ft.Column([
                    # HEADER
                    ft.Container(
                        content=ft.Column([
                            ft.Image(
                            src="Droid_mouss.png",
                            width=120,
                            height=120,
                            fit=ft.ImageFit.CONTAIN,
                            ),
                            ft.Text("Droid Assistant", size=22, weight=ft.FontWeight.BOLD, font_family="staround"),
                            ft.Text("L'Aventure Droid - Episode Bonus", size=16, font_family="staround"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=5
                    ),
                    ft.Divider(),
                    
                    # SECTION MÉMOIRE
                    ft.Text("💾 MÉMOIRE ET ARCHIVES", weight=ft.FontWeight.BOLD, color=ft.colors.CYAN),
                    ft.Container(
                        content=content_memoire,
                        height=150,
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_800),
                        border_radius=10,
                        bgcolor=ft.colors.BLACK12
                    ),
                    
                    ft.Row([
                        ft.FilledButton(
                            "CHARGER", 
                            icon=ft.icons.UPLOAD_FILE, 
                            on_click=action_charger, 
                            style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_900, color=ft.colors.WHITE),
                            expand=True
                        ),
                        ft.FilledButton(
                            "EFFACER", 
                            icon=ft.icons.DELETE_FOREVER, 
                            on_click=action_supprimer, 
                            style=ft.ButtonStyle(bgcolor=ft.colors.RED_900, color=ft.colors.WHITE),
                            expand=True
                        ),
                    ]),
                    ft.Row([
                        ft.FilledButton(
                            "RENOMMER", 
                            icon=ft.icons.DRIVE_FILE_RENAME_OUTLINE, 
                            on_click=action_renommer, 
                            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_900, color=ft.colors.WHITE),
                            expand=True
                        ),
                        ft.FilledButton(
                            "EXPORTER", 
                            icon=ft.icons.SEND, 
                            on_click=action_exporter, 
                            style=ft.ButtonStyle(bgcolor=ft.colors.PURPLE_900, color=ft.colors.WHITE),
                            expand=True
                        ),
                    ]),
                    
                    ft.Divider(),
                    
                    # SECTION CIRCUITS
                    ft.Text("🔌 CIRCUITS DU DROID", weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_GREY),
                    ft.OutlinedButton(
                        "EXPLORER LE STOCKAGE (SaveData)",
                        icon=ft.icons.FOLDER_OPEN,
                        on_click=self.action_ouvrir_dossier,
                        expand=True
                    ),
                    
                    ft.Divider(),
                    
                    # SECTION AJOUT INGRÉDIENTS
                    ft.Text("🛠️ NOUVELLE RESSOURCE", weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE),
                    ft.Container(
                        content=ft.Column([
                            radio_type,
                            ft.Row([t_nom, t_reco]),
                            ft.Row([t_sap, t_mousse]),
                            d_type_additif,
                            d_tox_he,
                            t_prop,
                            ft.FilledButton(
                                "ENREGISTRER DANS LA BASE",
                                icon=ft.icons.SAVE,
                                on_click=action_sauvegarder_ressource,
                                style=ft.ButtonStyle(bgcolor=ft.colors.ORANGE_800, color=ft.colors.WHITE),
                                width=400
                            )
                        ], spacing=10),
                        padding=15,
                        border=ft.border.all(1, ft.colors.ORANGE_900),
                        border_radius=10
                    ),
                    
                    ft.Divider(height=30, color="transparent"),
                    ft.FilledButton(
                        "← RETOUR AU LABORATOIRE",
                        on_click=lambda e: self.afficher_fenetre_1(),
                        height=50,
                        width=400,
                        style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_GREY_800, color=ft.colors.WHITE)
                    )
                ], scroll=ft.ScrollMode.ALWAYS),
                expand=True,
                padding=10
            )
        )
        self.page.update()
        
    def action_sauvegarder_finale(self, e):
        """Sauvegarde la recette actuelle"""
        self.emettre_son("old")
        try:
            resultats_chimiques = self.calculer_chimie_recette(self.recette)
            
            self.recette["resultats"] = resultats_chimiques
            self.recette["date_creation"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            nom_recette = self.recette.get("nom_recette", "Recette_Sans_Nom")
            nom_sauvegarde = self.memory.sauvegarder_recette(nom_recette, self.recette)
            
            self.afficher_info("Système", f"Recette archivée : {nom_sauvegarde}")
        
        except Exception as ex:
            self.afficher_erreur("Echec Archivage", f"Erreur : {str(ex)}")


def main(page: ft.Page):
    SoapMakerApp(page)


ft.app(target=main, assets_dir="assets")