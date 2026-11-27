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
- `scripts/` : compilation nxwright, rendu graphique Home et tests de non-régression.
- `tests/NX4832K035_011/7.0.0/source/` : sources nxwright éditables (pages, images, polices).
- `.github/workflows/nextion-*.yml` (hors `nextion/`) : lanceurs GitHub Actions obligatoirement situés dans le répertoire reconnu par GitHub.

La compilation **Waveshare ESP32-S3** et son empaquetage restent pilotés par `platformio.ini` et le point d'entrée `scripts/export_binaries.py`. Le `pio run` standard enchaîne désormais les **deux cibles `buildprog, nextion`**, y compris lorsque seul le projet Nextion a changé. La cible Nextion appelle la même chaîne `run_nextion.py` que `pio run -e nextion`, puis publie le TFT et le manifeste dans `binary/`. Les tests OTA firmware restent sous `scripts/tests/`.

### Chaîne nxwright actuellement maintenue

L'ancien décompilateur Nextion2Text, les scripts de patchage binaire HMI et
leurs workflows expérimentaux ont été retirés. Une **seule méthode** reste
active : modifier directement les sources nxwright dans
[`tests/NX4832K035_011/7.0.0/source/`](tests/NX4832K035_011/7.0.0/source/),
puis utiliser `pio run` (firmware + Nextion), `pio run -e nextion` (Nextion seul) ou `pio run -e nextion -t manifest` (copie seule).

Le générateur d'images actuel est `scripts/render_nx_home.py`. Les scripts
`scripts/test_nextion_wake.py` et `scripts/test_nextion_animation.py`
vérifient respectivement le redessin après veille et la rotation de la pompe.
Les sources HMI 7.0.0 précédemment validées restent accessibles dans
`backup/nextion-v7-validated-20261127` et la release 6.0.0 est conservée.

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

## Optimisation de la release 7.0.0 pour l'OTA

- **Fond Home uniformisé** : le dégradé et les halos de panneau ont été
  remplacés par des couleurs fixes pour réduire les données de l'image.
- **Turbine** : cinq couronnes colorées (70×70) indépendantes de onze petits
  centres rotatifs (48×48), au lieu de 55 images de turbine complètes.
  Le timer reste à 50 ms, les quatre pales tournent sur dix phases.
- **Atlas compact** : `1035×728` au lieu de `1035×1160`, avec
  repositionnement conjoint des appels `xpic`. Le RSSI conserve ses cinq
  couleurs et les jauges pH/ORP leurs cinq états.
- **OTA ESP32** : le TFT complet est maintenant préchargé dans des segments
  PSRAM de 64 KiB, vérifié par SHA-256 puis envoyé via UART. Il n'est plus
  nécessaire de réserver un seul bloc PSRAM de la taille du TFT. La réserve
  totale de **2 MiB** demeure obligatoire.

**Ordre de test :** après `pio run`, installer d'abord le nouveau firmware
ESP32 et son SPIFFS, puis tenter la mise à jour Nextion avec le nouveau TFT
et `manifest.json` publiés ensemble sur le serveur HTTP. L'ancienne version
du firmware ESP32 n'a pas encore le préchargement PSRAM segmenté.

## RSSI Wi-Fi réel pour le petit Nextion 7.0.0

L'ESP32 calcule la puissance Wi-Fi de la station et l'encode en cinq niveaux
dans les bits 16 à 18 de `globals.vaStates`. Le HMI NX4832K035_011 affiche
les arcs de force multicolores (gris déconnecté, rouge faible, jaune moyen,
cyan bon, vert excellent), à partir d'images précompilées. Les mises à
jour suivent la synchronisation Home, sans commande série supplémentaire.
Ce changement nécessite une mise à jour **firmware ESP32 + TFT Nextion**.

Les captures du design ne sont pas un test matériel ; valider sur le vrai
écran la sortie de veille, l'animation et la barre Wi-Fi.
