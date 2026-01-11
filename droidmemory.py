import os
import shutil
import json
import platform
from pathlib import Path
from fpdf import FPDF
from datetime import datetime


class DroidMemory:
    """Gestionnaire de fichiers et exports pour SoapMaker"""
    
    def __init__(self):
        # Détection du territoire (PC vs Android)
        self.base_dir = Path.home() / ".SoapMakerDroid"
        
        if platform.system() == "Windows":
            self.base_dir = Path(os.getcwd()) / "SaveData"
        else:
            # Sur Android, Path.home() pointe vers le stockage interne accessible de l'app
            self.base_dir = Path.home() / "SaveData"
        
        self.resources_dir = self.base_dir / "resources"
        self.recipes_dir = self.base_dir / "recettes"
        self.exports_dir = self.base_dir / "exports"
        
        # Création des dossiers
        self.resources_dir.mkdir(parents=True, exist_ok=True)
        self.recipes_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialisation des ressources
        self.verifier_integrite_ressources()
    
    def verifier_integrite_ressources(self):
        """Vérifie et initialise les fichiers JSON de base"""
        fichiers_base = ["huiles.json", "additifs.json", "addons_he.json"]
        source_assets = Path(os.getcwd()) / "assets"
        
        for fichier in fichiers_base:
            cible = self.resources_dir / fichier
            if not cible.exists():
                print(f"Initialisation de {fichier}...")
                try:
                    if (source_assets / fichier).exists():
                        shutil.copy(source_assets / fichier, cible)
                    else:
                        default_data = {fichier.split('.')[0]: []}
                        with open(cible, 'w', encoding='utf-8') as f:
                            json.dump(default_data, f)
                except Exception as e:
                    print(f"Erreur init ressources: {e}")
    
    # --- LECTURE/ÉCRITURE ---
    
    def charger_json(self, nom_fichier):
        """Charge un fichier JSON (ressource ou recette)"""
        if nom_fichier in ["huiles.json", "additifs.json", "addons_he.json"]:
            chemin = self.resources_dir / nom_fichier
        else:
            chemin = self.recipes_dir / nom_fichier
        
        if chemin.exists():
            with open(chemin, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def sauvegarder_ressource(self, nom_fichier, data):
        """Sauvegarde les modifications d'ingrédients"""
        chemin = self.resources_dir / nom_fichier
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def sauvegarder_recette(self, nom_recette, data):
        """Sauvegarde une recette avec gestion des doublons"""
        try:
            import re
            # Nettoyage du nom
            nom_clean = re.sub(r'[\\/*?:"<>|]', "", nom_recette)
            nom_base = nom_clean.replace(' ', '_')
            
            # Gestion des doublons
            compteur = 0
            while True:
                suffixe = f"_{compteur}" if compteur > 0 else ""
                nom_final = f"{nom_base}{suffixe}.json"
                chemin = self.recipes_dir / nom_final
                
                if not chemin.exists():
                    break
                compteur += 1
            
            # Force la création du dossier
            self.recipes_dir.mkdir(parents=True, exist_ok=True)
            
            # Écriture
            with open(chemin, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return nom_final  # Retourne le nom réel sauvegardé
        
        except Exception as e:
            print(f"Erreur écriture DroidMemory: {e}")
            raise
    
    def lister_recettes(self):
        """Liste les fichiers recettes disponibles"""
        try:
            return sorted([f.name for f in self.recipes_dir.glob("*.json")])
        except:
            return []
    
    def supprimer_recette(self, nom_fichier):
        """Supprime une recette"""
        chemin = self.recipes_dir / nom_fichier
        if chemin.exists():
            os.remove(chemin)
    
    def renommer_recette(self, ancien_nom, nouveau_nom):
        """Renomme une recette"""
        if not nouveau_nom.endswith(".json"):
            nouveau_nom += ".json"
        ancien_chemin = self.recipes_dir / ancien_nom
        nouveau_chemin = self.recipes_dir / nouveau_nom
        
        if ancien_chemin.exists():
            os.rename(ancien_chemin, nouveau_chemin)
    
    # --- EXPORT PDF ---
    
    def generer_pdf_recette(self, recette, nom_fichier=None):
        """
        Génère un PDF propre à partir d'une recette
        Retourne le chemin du fichier créé
        """
        try:
            # Nom du fichier
            if not nom_fichier:
                date_str = datetime.now().strftime("%Y%m%d_%H%M")
                nom_recette = recette.get('nom_recette', 'Recette')
                nom_fichier = f"{nom_recette}_{date_str}.pdf"
            
            # Nettoyage du nom
            import re
            nom_fichier = re.sub(r'[\\/*?:"<>|]', "", nom_fichier)
            if not nom_fichier.endswith('.pdf'):
                nom_fichier += '.pdf'
            
            chemin_sortie = self.exports_dir / nom_fichier
            
            # Création du PDF avec fpdf2 (support UTF-8 natif)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Chemin vers les polices
            font_dir = Path(os.getcwd()) / "assets" / "fonts"
            
            # Ajout des polices DejaVu (Regular et Bold)
            pdf.add_font("DejaVu", "", str(font_dir / "DejaVuSans.ttf"))
            pdf.add_font("DejaVu", "B", str(font_dir / "DejaVuSans-Bold.ttf"))
            pdf.add_font("DejaVu", "I", str(font_dir / "DejaVuSans-Oblique.ttf"))
            
            pdf.set_font("DejaVu", size=12)
            
            # En-tête
            pdf.set_font("DejaVu", "B", 18)
            pdf.cell(0, 10, recette.get('nom_recette', 'Recette de Savon'), ln=True, align="C")
            
            pdf.set_font("DejaVu", "I", 11)
            pdf.cell(0, 8, f"Date : {recette.get('date_creation', datetime.now().strftime('%Y-%m-%d'))}", ln=True, align="C")
            pdf.ln(5)
            
            # Paramètres
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, "PARAMÈTRES", ln=True)
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 6, f"- Surgraissage : {recette.get('surgras', 5)}%", ln=True)
            pdf.cell(0, 6, f"- Proportion liquide : {recette.get('proportion_eau', 30)}%", ln=True)
            pdf.ln(5)
            
            # Phase Grasse
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, "PHASE GRASSE (Corps Gras)", ln=True)
            pdf.set_font("DejaVu", "", 10)
            
            resultats = recette.get("resultats", {})
            detail_huiles = resultats.get("detail_huiles_g", recette.get("corps_gras", {}))
            
            for huile, poids in detail_huiles.items():
                if isinstance(poids, (int, float)):
                    pdf.cell(0, 6, f"  - {huile} : {poids:.1f} g", ln=True)
            pdf.ln(3)
            
            # Phase Aqueuse
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, "SOLUTION DE SOUDE (DANGER - Gants et lunettes obligatoires)", ln=True)
            pdf.set_font("DejaVu", "", 10)
            
            naoh = resultats.get('poids_soude', 0)
            eau = resultats.get('poids_eau', 0)
            substitut = resultats.get('poids_substitut', 0)
            sub_nom = recette.get('substitut_liquide', 'Aucun')
            
            pdf.cell(0, 6, f"  - Soude caustique (NaOH) : {naoh:.2f} g", ln=True)
            pdf.cell(0, 6, f"  - Eau distillée : {eau:.1f} g", ln=True)
            if substitut > 0 and sub_nom != "Aucun":
                pdf.cell(0, 6, f"  - {sub_nom} : {substitut:.1f} g", ln=True)
            pdf.ln(3)
            
            # Ajouts à la trace
            additifs = recette.get("additifs", {})
            he = recette.get("he", {})

            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, "AJOUTS À LA TRACE", ln=True)
            pdf.set_font("DejaVu", "", 10)

            # Vérifier s'il y a des ajouts
            a_des_ajouts = False

            for nom, poids in additifs.items():
                if poids > 0:
                    pdf.cell(0, 6, f"  - {nom} : {poids} g", ln=True)
                    a_des_ajouts = True

            for nom, poids in he.items():
                if poids > 0:
                    pdf.cell(0, 6, f"  - HE {nom} : {poids} g", ln=True)
                    a_des_ajouts = True

            if not a_des_ajouts:
                pdf.cell(0, 6, "  - Rien", ln=True)

            pdf.ln(3)
            
            # Totaux
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 8, "TOTAUX", ln=True)
            pdf.set_font("DejaVu", "", 10)
            
            total_frais = resultats.get('total_frais', 0)
            total_cure = resultats.get('total_cure', 0)
            volume = resultats.get('volume', 0)
            
            pdf.cell(0, 6, f"  - Poids pâte fraîche : {total_frais:.1f} g", ln=True)
            pdf.cell(0, 6, f"  - Poids après cure (4-6 sem) : ~{total_cure:.1f} g", ln=True)
            pdf.cell(0, 6, f"  - Volume de moule nécessaire : ~{volume:.0f} ml", ln=True)
            
            # Pied de page
            pdf.ln(10)
            pdf.set_font("DejaVu", "I", 9)
            pdf.cell(0, 6, "Généré par SoapMaker Droid Edition", ln=True, align="C")
            
            # Sauvegarde
            pdf.output(str(chemin_sortie))
            
            return str(chemin_sortie)
        
        except Exception as e:
            print(f"Erreur génération PDF : {e}")
            raise
    
    def generer_texte_mail(self, recette):
        """
        Génère un texte propre pour envoi par mail
        Retourne une string formatée
        """
        lignes = []
        lignes.append(f"RECETTE : {recette.get('nom_recette', 'Sans nom')}")
        lignes.append("=" * 60)
        lignes.append(f"Date : {recette.get('date_creation', datetime.now().strftime('%Y-%m-%d'))}")
        lignes.append(f"Surgraissage : {recette.get('surgras', 5)}% | Eau : {recette.get('proportion_eau', 30)}%")
        lignes.append("")
        
        # Phase grasse
        resultats = recette.get("resultats", {})
        detail_huiles = resultats.get("detail_huiles_g", recette.get("corps_gras", {}))
        
        lignes.append("[1] PHASE GRASSE")
        for huile, poids in detail_huiles.items():
            if isinstance(poids, (int, float)):
                lignes.append(f"  - {huile} : {poids:.1f} g")
        lignes.append("")
        
        # Solution de soude
        lignes.append("[2] SOLUTION DE SOUDE (DANGER)")
        naoh = resultats.get('poids_soude', 0)
        eau = resultats.get('poids_eau', 0)
        substitut = resultats.get('poids_substitut', 0)
        sub_nom = recette.get('substitut_liquide', 'Aucun')
        
        lignes.append(f"  - NaOH : {naoh:.2f} g")
        lignes.append(f"  - Eau : {eau:.1f} g")
        if substitut > 0 and sub_nom != "Aucun":
            lignes.append(f"  - {sub_nom} : {substitut:.1f} g")
        lignes.append("")
        
        # Ajouts
        additifs = recette.get("additifs", {})
        he = recette.get("he", {})

        lignes.append("[3] AJOUTS À LA TRACE")

        a_des_ajouts = False
        for nom, poids in additifs.items():
            if poids > 0:
                lignes.append(f"  - {nom} : {poids} g")
                a_des_ajouts = True

        for nom, poids in he.items():
            if poids > 0:
                lignes.append(f"  - HE {nom} : {poids} g")
                a_des_ajouts = True

        if not a_des_ajouts:
            lignes.append("  - Rien")

        lignes.append("")
        
        # Totaux
        lignes.append("=" * 60)
        total_frais = resultats.get('total_frais', 0)
        total_cure = resultats.get('total_cure', 0)
        
        lignes.append(f"POIDS PÂTE FRAÎCHE : {total_frais:.1f} g")
        lignes.append(f"APRÈS CURE (4-6 sem) : ~{total_cure:.1f} g")
        lignes.append("")
        lignes.append("Généré par SoapMaker Droid Edition")
        
        return "\n".join(lignes)