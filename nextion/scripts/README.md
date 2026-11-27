# Outils de compilation et validation Nextion

Tous les scripts HMI spécifiques au projet Nextion sont regroupés ici.

| Script | Usage |
|---|---|
| `build_3p5_v7_hmi.py` | Générateur historique 6.0.0 vers 7.0.0 ; ne pas le publier sur la version moderne |
| `build_3p5_v7_modern.py` | Générer les images et la page Home expérimentales 7.0.0 du NX4832K035_011 |
| `validate_3p5_v7_modern.py` | Vérification de l'intégrité de la version 7.0.0 moderne |
| `compare_3p5_hmi.py` | Comparaison historique HMI 6.0.0 / 7.0.0 |
| `audit_3p5_nxwright.py` | Audit nxwright en lecture seule : extraction, contrôles et reconstruction |

**Périmètre unique :** Nextion NX4832K035_011 (480 × 320), version 7.0.0.
Ne jamais modifier les sources ou TFT des Nextion 5″/7″ via ces outils.

Les scripts sont lancés depuis la racine du dépôt. Leurs imports Python mutuels
restent valides puisque tous les scripts ont été déplacés ensemble.

Les workflows correspondants restent dans `.github/workflows/` (exigence GitHub Actions).
Le hook général de packaging `scripts/export_binaries.py` demeure à sa place pour
la compilation Waveshare/OTA ; il lit `nextion/releases/<version>/*.tft` sans compiler de HMI.

L'audit nxwright ne produit aucun firmware de production et doit actuellement
signaler que la page Home moderne n'est pas entièrement reconnue.
