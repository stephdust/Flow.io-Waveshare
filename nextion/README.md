# Ressources Nextion flow.io

Voir [Modes PoolLogic et adaptation des écrans Nextion](../docs/integration/poollogic-operating-modes.md).

Les fichiers `.HMI` sont les sources éditables dans Nextion Editor. Les fichiers `.tft` sont les images compilées à transférer vers un écran précis.

Les fichiers Nextion sont rangés **uniquement par version** dans `releases/<version>/`. Les anciens `.tft` à la racine et le répertoire `src/` ont été supprimés pour éviter les doublons.

**Convention de nommage commune aux sources et binaires :** `FlowIO_Nextion_<MODELE_COMPATIBLE>-<VERSION>.HMI` pour le projet source, et même nom en `.tft` pour le firmware compilé. L'extension `.HMI` n'est pas analysée par le script d'export des TFT.

**Cas 800 × 480 (6.0.0) :** une source HMI historique unique sert aux écrans 5″ (`NX8048P050_011`) et 7″ (`NX8048P070_011`). Elle est rangée sous le nom canonique `FlowIO_Nextion_NX8048P050_011-6.0.0.HMI` ; cela **n'affirme pas** que le fichier compilé est utilisable indifféremment sur les deux écrans. Les TFT restent séparés par modèle.

La valeur de `common.nextion_firmware_version` dans [`platformio.ini`](../platformio.ini) est désormais **7.0.0**. Le HMI corrigé de test, qui s'ouvre et compile dans Nextion Editor, est disponible dans [`releases/7.0.0/`](releases/7.0.0/). **Attention : le TFT 7.0.0 compilé n'est pas encore présent sur GitHub** : le déposer dans ce dossier sous le nom `FlowIO_Nextion_NX4832K035_011-7.0.0.tft`, puis le commiter. En attendant, un clone propre échouera à l'étape d'export Nextion lors d'un build complet.

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
