# Outils de compilation et validation Nextion

Tous les scripts HMI spécifiques au projet Nextion sont regroupés ici.

| Script | Usage |
|---|---|
| `build_3p5_v7_hmi.py` | Générateur historique 6.0.0 vers 7.0.0 ; ne pas le publier sur la version moderne |
| `build_3p5_v7_modern.py` | **Bibliothèque de rendu d'images uniquement.** Ne plus lancer son patchage binaire HMI : l'ancienne méthode a produit un HMI invalide |
| `validate_3p5_v7_modern.py` | Vérification de l'intégrité de la version 7.0.0 moderne |
| `compare_3p5_hmi.py` | Comparaison historique HMI 6.0.0 / 7.0.0 |
| `audit_3p5_nxwright.py` | Audit nxwright en lecture seule : extraction, contrôles et reconstruction |
| `modernize_3p5_nxsource.py` | Modifier les textes et images d'un projet NX4832K035 *extrait par nxwright* ; sans patchage binaire |
| `compile_nxwright_test.sh` | Compiler un TFT de test depuis les sources, avec blocages de nom/version/modèle et firmware Nextion 1.68.2 |

**Périmètre unique :** Nextion NX4832K035_011 (480 × 320), version 7.0.0.
Ne jamais modifier les sources ou TFT des Nextion 5″/7″ via ces outils.

Les scripts sont lancés depuis la racine du dépôt. Leurs imports Python mutuels
restent valides puisque tous les scripts ont été déplacés ensemble.

Les workflows correspondants restent dans `.github/workflows/` (exigence GitHub Actions).
Le hook général de packaging `scripts/export_binaries.py` demeure à sa place pour
la compilation Waveshare/OTA ; il lit `nextion/releases/<version>/*.tft` sans compiler de HMI.

L'audit nxwright continue de signaler que **l'ancien HMI graphique patché en binaire** n'est pas entièrement reconnu. Le **nouveau workflow nxwright texte → HMI → TFT** est au contraire compatible et réussi : [résultats du workflow](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/46004942701). Il utilise uniquement le HMI 7.0.0 fonctionnel comme base et n'écrit pas dans la release officielle. Validation sur matériel encore nécessaire.


## Entrée PlatformIO de compilation Nextion

`platformio.ini` possède une section isolée **`[env:nextion]`** :

```bash
pio run -e nextion
```

Cette commande exécute uniquement la chaîne du **NX4832K035_011, 480 × 320, version 7.0.0** :
`nxwright check` → `nxwright build` → réextraction et validation du HMI →
`nxwright compile --download` → vérification TFT → copie dans
`nextion/releases/7.0.0/` → export dans `binary/` → régénération
de `binary/manifest.json`.

Pour simplement republier le **TFT déjà compilé et le manifeste**, sans
installer nxwright, sans compilation ni SPIFFS :

```bash
pio run -e nextion -t manifest
```

Ces deux cibles utilisent **le même environnement PlatformIO**, avec une seule
implémentation dans `nextion/scripts/` :
`pio_nextion_targets.py` → `run_nextion.py` →
`refresh_nextion_manifest.py` (appel interne à l'exporteur existant).

Lors de la première compilation Nextion complète, une installation isolée de
nxwright à un commit Git précis dans `.pio/nextion-nxwright-venv/` et le
téléchargement du firmware système Nextion Editor peuvent nécessiter Internet.
Les compilations suivantes réutilisent l'environnement. Aucun code C++
ESP32 ni image SPIFFS n'est construit.

La version reste `7.0.0`. Sur notre fork `dev`, les HMI/TFT sont
expérimentaux jusqu'aux tests réels. La branche amont de Christophe et les
modèles Nextion 5″/7″ ne sont pas modifiés.

**Mise à jour à distance :** après la commande rapide, il faut publier le TFT
**et** `binary/manifest.json` ensemble au même emplacement HTTP. Sinon Flow.io
peut afficher `Nextion artifact HTTP response invalid` malgré un manifeste
local correct. Les manifests `flowio-release-*.json` / `release.json` et le
ZIP OTA ESP32/SPIFFS sont indépendants et ne sont pas régénérés ici.
