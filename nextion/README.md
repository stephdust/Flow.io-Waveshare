# Ressources Nextion flow.io

Voir [Modes PoolLogic et adaptation des écrans Nextion](../docs/integration/poollogic-operating-modes.md).

Les fichiers `.HMI` sont les sources éditables dans Nextion Editor. Les fichiers `.tft` sont les images compilées à transférer vers un écran précis.

Les fichiers Nextion sont rangés **uniquement par version** dans `releases/<version>/`. Les anciens `.tft` à la racine et le répertoire `src/` ont été supprimés pour éviter les doublons.

**Convention de nommage commune aux sources et binaires :** `FlowIO_Nextion_<MODELE_COMPATIBLE>-<VERSION>.HMI` pour le projet source, et même nom en `.tft` pour le firmware compilé. L'extension `.HMI` n'est pas analysée par le script d'export des TFT.

**Cas 800 × 480 (6.0.0) :** une source HMI historique unique sert aux écrans 5″ (`NX8048P050_011`) et 7″ (`NX8048P070_011`). Elle est rangée sous le nom canonique `FlowIO_Nextion_NX8048P050_011-6.0.0.HMI` ; cela **n'affirme pas** que le fichier compilé est utilisable indifféremment sur les deux écrans. Les TFT restent séparés par modèle.

La valeur de `common.nextion_firmware_version` dans [`platformio.ini`](../platformio.ini) reste **7.0.0**.
Sur le **fork `stephdust/dev`**, les fichiers
[`releases/7.0.0/`](releases/7.0.0/) contiennent maintenant le **nouveau HMI et
le TFT 7.0.0 compilés avec nxwright** pour le `NX4832K035_011`.
Les sources éditables, la prévisualisation et les logs sont committés dans
[`tests/NX4832K035_011/7.0.0/`](tests/NX4832K035_011/7.0.0/).
Ce sont les **fichiers de développement et de test de notre fork** ; leur
comportement sur le véritable Nextion doit encore être validé.

**La référence amont est `christophebelmont/Flow.io-Waveshare:dev` et elle
n'est pas modifiée par ce travail. Aucun PR n'est ouvert à ce stade.**
Une sauvegarde de notre ancienne 7.0.0 fonctionnelle est disponible dans
[`backup/nextion-v7-validated-20261127`](https://github.com/stephdust/Flow.io-Waveshare/tree/backup/nextion-v7-validated-20261127).
Les sources/TFT des Nextion **5″ et 7″ restent strictement inchangés**.

La [version 6.0.0](releases/6.0.0/) reste archivée et intacte, avec ses sources et ses TFT ; elle n'est plus sélectionnée par `platformio.ini`.

| Modèle | Définition | TFT de référence **6.0.0** (archives) |
|---|---:|---|
| NX4832K035 | 480×320 | [`FlowIO_Nextion_NX4832K035_011-6.0.0.tft`](releases/6.0.0/FlowIO_Nextion_NX4832K035_011-6.0.0.tft) |
| NX8048P050-011R | 800×480 | [`FlowIO_Nextion_NX8048P050_011-6.0.0.tft`](releases/6.0.0/FlowIO_Nextion_NX8048P050_011-6.0.0.tft) |
| NX8048P070-011R | 800×480 | [`FlowIO_Nextion_NX8048P070_011-6.0.0.tft`](releases/6.0.0/FlowIO_Nextion_NX8048P070_011-6.0.0.tft) |

Voir [Écrans Nextion](../docs/hardware/nextion-displays.md) pour le choix du modèle, le câblage et le transfert du firmware.

## Convention des artefacts

Les fichiers publiés suivent le contrat
`FlowIO_Nextion_<MODELE_COMPATIBLE>-<VERSION>.tft`. Le modèle compatible omet
uniquement le marqueur tactile `R` ou `C`: les variantes résistive et capacitive
d'un même modèle utilisent le même TFT. Les autres suffixes matériels restent
significatifs.

Lors de la compilation FlowIOS3, les TFT de la release correspondant à
`TFT_FIRMW` sont copiés dans `binary/`. Le générateur reporte dans
`manifest.json` la clé `display_compatibility` extraite du nom et refuse les
noms ambigus ou les doublons modèle/version.

## Organisation des ressources Nextion

- `releases/<version>/` : HMI et TFT par version et modèle, avec éventuelles prévisualisations.
- `scripts/` : générateurs HMI, scripts de comparaison, de validation et d'audit nxwright.
- `docs/` : procédures Nextion et rapports d'audit.
- `.github/workflows/nextion-*.yml` (hors `nextion/`) : lanceurs GitHub Actions obligatoirement situés dans le répertoire reconnu par GitHub.

La compilation **Waveshare ESP32-S3** et son empaquetage restent pilotés par `platformio.ini` et le point d'entrée partagé `scripts/export_binaries.py`. Celui-ci lit les `.tft` dans `nextion/releases/<version>/`, et ne compile ni ne modifie les HMI. Il reste sous `scripts/` pour ne pas casser les hooks PlatformIO d'autres sous-systèmes. Les tests OTA firmware restent sous `scripts/tests/`.

### Tester nxwright : audit HMI et génération expérimentale de TFT

Voir [la procédure et ses limites](docs/nxwright-7-0-audit.md) ; l'audit compare uniquement le HMI 7.0.0 du `NX4832K035_011` à sa source sauvegardée. Les HMI/TFT des Nextion 5″ et 7″ ne doivent pas être modifiés.


La source nxwright de la nouvelle Home se trouve dans `nextion/tests/NX4832K035_011/7.0.0/source/` et a été préparée avec `modernize_3p5_nxsource.py`. Sa compilation passe **uniquement par `[env:nextion]` dans PlatformIO** : elle produit le HMI/TFT dans `nextion/releases/7.0.0/` puis exporte `binary/manifest.json` sur notre fork `dev`. Le firmware système officiel est récupéré par nxwright lors du premier build. Rien n'est encore proposé à Christophe.


## Compilation Nextion via PlatformIO (méthode unique)

**Mémo :** `pio run -e nextion` = compilation HMI/TFT **+** copie dans `binary/` **+** manifeste. `pio run -e nextion -t manifest` = copie et manifeste **seulement**. Le paramètre `-t manifest` n'est pas obligatoire lorsque l'on recompile.

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
