# Ressources Nextion flow.io

Voir [Modes PoolLogic et adaptation des écrans Nextion](../docs/integration/poollogic-operating-modes.md).

Les fichiers `.HMI` sont les sources éditables dans Nextion Editor. Les fichiers `.tft` sont les images compilées à transférer vers un écran précis.

Les fichiers Nextion sont rangés **uniquement par version** dans `releases/<version>/`. Les anciens `.tft` à la racine et le répertoire `src/` ont été supprimés pour éviter les doublons.

**Convention de nommage commune aux sources et binaires :** `FlowIO_Nextion_<MODELE_COMPATIBLE>-<VERSION>.HMI` pour le projet source, et même nom en `.tft` pour le firmware compilé. L'extension `.HMI` n'est pas analysée par le script d'export des TFT.

**Cas 800 × 480 (6.0.0) :** une source HMI historique unique sert aux écrans 5″ (`NX8048P050_011`) et 7″ (`NX8048P070_011`). Elle est rangée sous le nom canonique `FlowIO_Nextion_NX8048P050_011-6.0.0.HMI` ; cela **n'affirme pas** que le fichier compilé est utilisable indifféremment sur les deux écrans. Les TFT restent séparés par modèle.

La valeur de `common.nextion_firmware_version` dans [`platformio.ini`](../platformio.ini) reste **7.0.0**. La source HMI **de référence** dans [`releases/7.0.0/`](releases/7.0.0/) est la **7.0.0 déjà validée sur écran réel**, également sauvegardée sur [`backup/nextion-v7-validated-20261127`](https://github.com/stephdust/Flow.io-Waveshare/tree/backup/nextion-v7-validated-20261127). L'ancien HMI graphique créé par patchage binaire a été retiré de la release après affichage de rectangles blancs sur l'écran réel. Le **nouveau design expérimental**, généré en modifiant les sources texte/PNG avec nxwright et en reconstruisant HMI + TFT, est disponible uniquement dans [l'artefact de test GitHub Actions](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/46004942701). Il doit être validé sur le matériel avant toute publication officielle. **Aucun TFT 7.0.0 de production n'est publié sur GitHub.** Les fichiers des Nextion 5″/7″ restent strictement inchangés.

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


La compilation nxwright de la nouvelle Home utilise `nextion/scripts/modernize_3p5_nxsource.py` et `nextion/scripts/compile_nxwright_test.sh`. Le firmware système Nextion Editor 1.68.2 est acquis par `nxwright compile --download` dans un runner temporaire. Ces artefacts expérimentaux ne sont ni copiés dans `binary/`, ni utilisés par `platformio.ini`.
