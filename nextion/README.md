# Ressources Nextion flow.io

Voir [Modes PoolLogic et adaptation des écrans Nextion](../docs/integration/poollogic-operating-modes.md).

Les fichiers `.HMI` sont les sources éditables dans Nextion Editor. Les fichiers `.tft` sont les images compilées à transférer vers un écran précis.

Les fichiers Nextion sont rangés **uniquement par version** dans `releases/<version>/`. Les anciens `.tft` à la racine et le répertoire `src/` ont été supprimés pour éviter les doublons.

**Convention de nommage commune aux sources et binaires :** `FlowIO_Nextion_<MODELE_COMPATIBLE>-<VERSION>.HMI` pour le projet source, et même nom en `.tft` pour le firmware compilé. L'extension `.HMI` n'est pas analysée par le script d'export des TFT.

**Cas 800 × 480 (6.0.0) :** une source HMI historique unique sert aux écrans 5″ (`NX8048P050_011`) et 7″ (`NX8048P070_011`). Elle est rangée sous le nom canonique `FlowIO_Nextion_NX8048P050_011-6.0.0.HMI` ; cela **n'affirme pas** que le fichier compilé est utilisable indifféremment sur les deux écrans. Les TFT restent séparés par modèle.

La valeur de `common.nextion_firmware_version` dans [`platformio.ini`](../platformio.ini) reste **7.0.0**. Le **nouveau HMI graphique 7.0.0 pour le NX4832K035_011 (480 × 320 seulement)** se trouve dans [`releases/7.0.0/`](releases/7.0.0/). Son ouverture et sa compilation avec Nextion Editor sont **encore à tester**. L'ancien HMI 7.0.0 validé est sauvegardé sur [`backup/nextion-v7-validated-20261127`](https://github.com/stephdust/Flow.io-Waveshare/tree/backup/nextion-v7-validated-20261127). **Le TFT 7.0.0 compilé n'est pas présent sur GitHub** : après compilation et vérification, déposer le fichier `FlowIO_Nextion_NX4832K035_011-7.0.0.tft` dans la release et le commiter. Les fichiers des Nextion 5″/7″ restent strictement inchangés.

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
